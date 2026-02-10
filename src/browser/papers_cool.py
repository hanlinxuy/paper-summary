"""papers.cool Kimi summary scraper using Playwright"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import BaseScraper
from .manager import BrowserManager

logger = logging.getLogger(__name__)


@dataclass
class KimiSummary:
    """Kimi-generated paper summary"""

    paper_id: str
    summary: str = ""
    key_points: list[str] = None  # type: ignore[assignment]
    methods: Optional[str] = None
    contributions: Optional[str] = None
    generated_at: Optional[str] = None

    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []


class PapersCoolScraper(BaseScraper):
    """Scrape Kimi summaries from papers.cool"""

    BASE_URL = "https://papers.cool"

    def __init__(
        self,
        browser_manager: BrowserManager,
        cache_dir: Optional[Path] = None,
        cache_ttl: int = 86400,
        timeout: int = 30000,
    ):
        super().__init__(browser_manager, cache_dir, cache_ttl, timeout)

    def _fetch_page(self, url: str) -> dict:
        """Fetch papers.cool page content"""
        page = self.browser_manager.new_page()

        try:
            logger.info(f"Fetching papers.cool page: {url}")
            response = page.goto(
                url, wait_until="domcontentloaded", timeout=self.timeout
            )

            if response.status >= 400:
                raise ConnectionError(f"HTTP {response.status}: {url}")

            # Wait for page to stabilize
            page.wait_for_load_state("networkidle", timeout=10000)

            # Extract paper ID from URL
            paper_id_match = re.search(r"/arxiv/(\d+\.\d+)", url)
            paper_id = paper_id_match.group(1) if paper_id_match else ""

            # Find and click the Kimi button
            # Button ID format: "kimi-{paper_id}" e.g., "kimi-2602.06960"
            kim_id = f"kimi-{paper_id}"
            kim_button = page.locator(f"a[id='{kim_id}']")

            if kim_button.count() > 0:
                logger.info(f"Clicking Kimi button for {paper_id}")
                kim_button.click()
                # Wait for Kimi summary to load
                page.wait_for_timeout(3000)
            else:
                logger.warning(f"Kimi button not found: {kim_id}")

            # Extract full page text
            full_text = page.evaluate("() => document.body.innerText")

            # Parse the summary content
            data = self._parse_summary(paper_id, full_text)
            data["url"] = url

            return data

        except Exception as e:
            logger.error(f"Failed to fetch papers.cool page: {e}")
            return {
                "paper_id": "",
                "summary": "",
                "key_points": [],
                "methods": None,
                "contributions": None,
                "generated_at": None,
                "error": str(e),
            }
        finally:
            page.close()

    def _parse_summary(self, paper_id: str, full_text: str) -> dict:
        """Parse Kimi summary from page text"""
        # Extract key sections using pattern matching
        summary = ""
        key_points = []
        methods = None
        contributions = None

        # Split by Q&A patterns
        q_patterns = [
            r"Q1[:：]\s*(.+?)(?=Q2|$)",
            r"问题[:：]\s*(.+?)(?=相关工作|$)",
        ]
        method_patterns = [
            r"Q2[:：]\s*(.+?)(?=Q3|$)",
            r"相关工作[:：]\s*(.+?)(?=方法|$)",
        ]
        exp_patterns = [
            r"Q3[:：]\s*(.+?)(?=Q4|$)",
            r"方法[:：]\s*(.+?)(?=实验|$)",
        ]
        result_patterns = [
            r"Q4[:：]\s*(.+?)(?=Q5|$)",
            r"实验结果[:：]\s*(.+?)(?=未来|$)",
        ]
        future_patterns = [
            r"Q5[:：]\s*(.+?)(?=Q6|$)",
            r"未来工作[:：]\s*(.+?)(?=总结|$)",
        ]
        conclusion_patterns = [
            r"Q6[:：]\s*(.+?)(?=关键词|$)",
            r"总结[:：]\s*(.+?)(?=关键词|$)",
        ]

        # Combine all Q&A into summary
        sections = []
        for pattern in (
            q_patterns
            + method_patterns
            + exp_patterns
            + result_patterns
            + future_patterns
            + conclusion_patterns
        ):
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                sections.append(match.group(1).strip())

        summary = "\n\n".join(sections) if sections else full_text[:5000]

        # Extract key points (bullet points or numbered items)
        bullet_pattern = r"[•\-\*]\s*(.+?)(?=[•\-\*]|$)"
        number_pattern = r"\d+[.:）]\s*(.+?)(?=\d+[.:）]|$)"

        for pattern in [bullet_pattern, number_pattern]:
            matches = re.findall(pattern, summary, re.DOTALL)
            if matches:
                key_points = [m.strip() for m in matches if len(m.strip()) > 10][:10]
                break

        # Extract methods section
        for pattern in method_patterns:
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                methods = match.group(1).strip()[:500]
                break

        # Extract contributions/innovations
        contrib_patterns = [
            r"创新点[:：]\s*(.+?)(?=Q|$)",
            r"主要贡献[:：]\s*(.+?)(?=Q|$)",
        ]
        for pattern in contrib_patterns:
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                contributions = match.group(1).strip()[:500]
                break

        return {
            "paper_id": paper_id,
            "summary": summary,
            "key_points": key_points,
            "methods": methods,
            "contributions": contributions,
            "generated_at": None,
        }

    def scrape_kimi_summary(self, paper_id: str, use_cache: bool = True) -> KimiSummary:
        """Scrape Kimi summary for a paper"""
        url = f"{self.BASE_URL}/arxiv/{paper_id}"
        data = self.scrape(url, use_cache)

        if "error" in data:
            logger.warning(
                f"Failed to fetch Kimi summary for {paper_id}: {data['error']}"
            )

        return KimiSummary(
            paper_id=data["paper_id"] or paper_id,
            summary=data["summary"],
            key_points=data["key_points"],
            methods=data["methods"],
            contributions=data["contributions"],
            generated_at=data["generated_at"],
        )


def create_papers_cool_scraper(
    cache_dir: Optional[Path] = None,
    cache_ttl: int = 86400,
    timeout: int = 30000,
) -> PapersCoolScraper:
    """Factory function to create PapersCoolScraper instance"""
    manager = BrowserManager()
    return PapersCoolScraper(manager, cache_dir, cache_ttl, timeout)
