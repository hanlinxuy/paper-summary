"""Playwright Browser Management Module"""

from .manager import BrowserManager, get_browser_manager
from .base import BaseScraper
from .arxiv import ArxivScraper, ArxivPaper, create_arxiv_scraper
from .papers_cool import PapersCoolScraper, KimiSummary, create_papers_cool_scraper

__all__ = [
    "BrowserManager",
    "get_browser_manager",
    "BaseScraper",
    "ArxivScraper",
    "ArxivPaper",
    "create_arxiv_scraper",
    "PapersCoolScraper",
    "KimiSummary",
    "create_papers_cool_scraper",
]
