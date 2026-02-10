"""papers.cool Kimi摘要API客户端 (支持 Playwright 抓取和 API 回退)"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..config import get_config
from ..browser.papers_cool import PapersCoolScraper, KimiSummary as BrowserKimiSummary
from ..browser.manager import get_browser_manager

logger = logging.getLogger(__name__)


@dataclass
class KimiSummary:
    """Kimi生成的论文摘要"""

    paper_id: str
    summary: str = ""
    key_points: list[str] = None  # type: ignore[assignment]
    methods: Optional[str] = None
    contributions: Optional[str] = None
    raw_html: str = ""

    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []

    @property
    def full_content(self) -> str:
        return self.raw_html

    def extract_text_content(self) -> str:
        """提取纯文本内容"""
        soup = BeautifulSoup(self.raw_html, "lxml")
        text_parts = []

        for q in soup.find_all("p", class_="faq-q"):
            question = q.get_text(strip=True)
            answer = q.find_next_sibling("div", class_="faq-a")
            if answer:
                answer_text = answer.get_text(strip=True, separator="\n")
                text_parts.append(f"{question}\n{answer_text}\n")

        return "\n\n".join(text_parts)


def _convert_browser_summary(
    browser_summary: BrowserKimiSummary, raw_html: str = ""
) -> KimiSummary:
    """将浏览器抓取的摘要转换为 API 格式"""
    return KimiSummary(
        paper_id=browser_summary.paper_id,
        summary=browser_summary.summary,
        key_points=browser_summary.key_points,
        methods=browser_summary.methods,
        contributions=browser_summary.contributions,
        raw_html=raw_html,
    )


def fetch_kimi_summary(paper_id: str, use_browser: bool = True) -> KimiSummary:
    """获取papers.cool上的Kimi摘要 (支持 Playwright 抓取)"""
    config = get_config()

    # Try browser first if enabled
    if use_browser and config.browser.enabled:
        try:
            logger.info(f"Fetching Kimi summary for {paper_id} via Playwright...")

            cache_dir = Path(config.browser.cache_dir)
            cache_ttl = config.browser.cache_ttl
            timeout = config.browser.timeout

            browser_manager = get_browser_manager()
            scraper = PapersCoolScraper(
                browser_manager=browser_manager,
                cache_dir=cache_dir,
                cache_ttl=cache_ttl,
                timeout=timeout,
            )
            browser_summary = scraper.scrape_kimi_summary(paper_id, use_cache=True)

            if browser_summary.summary:
                logger.info(f"Successfully fetched Kimi summary for {paper_id}")
                return _convert_browser_summary(browser_summary)

        except Exception as e:
            logger.warning(f"Playwright fetch failed for {paper_id}: {e}")

    # Flex mode: only fallback to API if explicitly enabled
    if not config.flex_mode.enabled or not config.flex_mode.papers_cool_api:
        logger.warning(
            f"Playwright unavailable for {paper_id} Kimi summary and flex_mode is disabled. "
            "Skipping API fallback (flex_mode.papers_cool_api=false)."
        )
        return KimiSummary(paper_id=paper_id)

    # Fallback to API
    logger.info(f"Fetching Kimi summary for {paper_id} via API...")
    base_url = config.papers_cool.base_url.rstrip("/")
    endpoint = config.papers_cool.kimi_endpoint
    url = f"{base_url}{endpoint}?paper={paper_id}"

    headers = {
        "User-Agent": "PaperSummaryBot/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }

    response = requests.post(url, headers=headers, timeout=config.papers_cool.timeout)
    response.raise_for_status()

    raw_html = response.text

    soup = BeautifulSoup(raw_html, "lxml")

    # Try to extract FAQ-style content
    q1 = _extract_q_content(soup, "Q1")
    q2 = _extract_q_content(soup, "Q2")
    q3 = _extract_q_content(soup, "Q3")
    q4 = _extract_q_content(soup, "Q4")
    q5 = _extract_q_content(soup, "Q5")
    q6 = _extract_q_content(soup, "Q6")

    # Combine all Q&A into summary
    summary_parts = []
    if q1:
        summary_parts.append(f"问题：{q1}")
    if q2:
        summary_parts.append(f"相关工作：{q2}")
    if q3:
        summary_parts.append(f"方法：{q3}")
    if q4:
        summary_parts.append(f"实验：{q4}")
    if q5:
        summary_parts.append(f"未来工作：{q5}")
    if q6:
        summary_parts.append(f"总结：{q6}")

    summary = "\n\n".join(summary_parts) if summary_parts else ""

    # Extract key points
    key_points = []
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if len(text) > 10 and len(text) < 200:
            key_points.append(text)

    return KimiSummary(
        paper_id=paper_id,
        summary=summary,
        key_points=key_points,
        methods=q3,
        contributions=None,
        raw_html=raw_html,
    )


def _extract_q_content(soup: BeautifulSoup, q_label: str) -> str:
    """提取单个问答内容"""
    for q_tag in soup.find_all("p", class_="faq-q"):
        text = q_tag.get_text(strip=True)
        if f"{q_label}:" in text or q_label in text:
            answer_div = q_tag.find_next_sibling("div", class_="faq-a")
            if answer_div:
                return answer_div.get_text(strip=True)
    return ""
