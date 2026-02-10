"""arXiv page scraper using Playwright"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import BaseScraper
from .manager import BrowserManager

logger = logging.getLogger(__name__)


@dataclass
class ArxivPaper:
    """arXiv paper metadata"""

    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_date: str
    doi: Optional[str] = None
    pdf_url: str = ""
    comment: Optional[str] = None


class ArxivScraper(BaseScraper):
    """Scrape paper metadata from arXiv.org pages"""

    BASE_URL = "https://arxiv.org"

    def __init__(
        self,
        browser_manager: BrowserManager,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = 86400,
        timeout: int = 30000,
    ):
        super().__init__(browser_manager, cache_dir, cache_ttl, timeout)

    def _fetch_page(self, url: str) -> dict:
        """Fetch arXiv page content"""
        page = self.browser_manager.new_page()

        try:
            logger.info(f"Fetching arXiv page: {url}")
            response = page.goto(url, wait_until="networkidle", timeout=self.timeout)

            if response.status >= 400:
                raise ConnectionError(f"HTTP {response.status}: {url}")

            # Extract paper metadata
            data = self._extract_metadata(page)
            data["url"] = url

            return data

        except Exception as e:
            logger.error(f"Failed to fetch arXiv page: {e}")
            raise
        finally:
            page.close()

    def _extract_metadata(self, page) -> dict:
        """Extract paper metadata from page"""
        # Extract title
        title = page.evaluate(
            """() => {
                const el = document.querySelector('meta[name="citation_title"]');
                return el ? el.getAttribute('content') : '';
            }"""
        )

        # Extract authors
        authors = page.evaluate(
            """() => {
                const els = document.querySelectorAll('meta[name="citation_author"]');
                return Array.from(els).map(el => el.getAttribute('content'));
            }"""
        )

        # Extract abstract
        abstract = page.evaluate(
            """() => {
                const el = document.querySelector('meta[name="citation_abstract"]');
                return el ? el.getAttribute('content') : '';
            }"""
        )

        # Extract categories
        categories = page.evaluate(
            """() => {
                const els = document.querySelectorAll('meta[name="citation_keywords"]');
                if (els.length > 0) {
                    return els[0].getAttribute('content').split(',').map(c => c.trim());
                }
                // Fallback to subject class
                const subjectEl = document.querySelector('.subjects');
                return subjectEl ? subjectEl.textContent.split(',').map(s => s.trim()) : [];
            }"""
        )

        # Extract DOI
        doi = page.evaluate(
            """() => {
                const el = document.querySelector('meta[name="citation_doi"]');
                return el ? el.getAttribute('content') : null;
            }"""
        )

        # Extract published date
        published_date = page.evaluate(
            """() => {
                const el = document.querySelector('meta[name="citation_publication_date"]');
                return el ? el.getAttribute('content') : '';
            }"""
        )

        # Extract paper ID from URL
        paper_id = page.evaluate(
            """() => {
                const match = window.location.href.match(/(\\d{4}\\.\\d{4,5})/);
                return match ? match[1] : '';
            }"""
        )

        # Extract PDF URL
        pdf_url = page.evaluate(
            """() => {
                const link = document.querySelector('a[href*=".pdf"]');
                return link ? link.href : '';
            }"""
        )

        # Extract comment if available
        comment = page.evaluate(
            """() => {
                const commentEl = document.querySelector('.comments');
                return commentEl ? commentEl.textContent.replace('Comments:', '').trim() : null;
            }"""
        )

        return {
            "paper_id": paper_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "published_date": published_date,
            "doi": doi,
            "pdf_url": pdf_url,
            "comment": comment,
        }

    def scrape_paper(self, paper_id: str, use_cache: bool = True) -> ArxivPaper:
        """Scrape paper metadata by ID"""
        # Normalize paper ID
        if not re.match(r"\d{4}\.\d{4,5}", paper_id):
            raise ValueError(f"Invalid arXiv ID format: {paper_id}")

        url = f"{self.BASE_URL}/abs/{paper_id}"
        data = self.scrape(url, use_cache)

        return ArxivPaper(
            paper_id=data["paper_id"],
            title=data["title"],
            authors=data["authors"],
            abstract=data["abstract"],
            categories=data["categories"],
            published_date=data["published_date"],
            doi=data["doi"],
            pdf_url=data["pdf_url"],
            comment=data["comment"],
        )


def create_arxiv_scraper(
    cache_dir: Optional[Path] = None,
    cache_ttl: int = 86400,
    timeout: int = 30000,
) -> ArxivScraper:
    """Factory function to create ArxivScraper instance"""
    manager = BrowserManager()
    return ArxivScraper(manager, cache_dir, cache_ttl, timeout)
