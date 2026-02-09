"""papers.cool Kimi摘要API客户端"""

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..config import get_config


@dataclass
class KimiSummary:
    paper_id: str
    q1_problem: str
    q2_related: str
    q3_method: str
    q4_experiments: str
    q5_future: str
    q6_summary: str
    raw_html: str

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


def fetch_kimi_summary(paper_id: str) -> KimiSummary:
    """获取papers.cool上的Kimi摘要"""
    config = get_config()
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

    q1 = _extract_q_content(soup, "Q1")
    q2 = _extract_q_content(soup, "Q2")
    q3 = _extract_q_content(soup, "Q3")
    q4 = _extract_q_content(soup, "Q4")
    q5 = _extract_q_content(soup, "Q5")
    q6 = _extract_q_content(soup, "Q6")

    return KimiSummary(
        paper_id=paper_id,
        q1_problem=q1 or "",
        q2_related=q2 or "",
        q3_method=q3 or "",
        q4_experiments=q4 or "",
        q5_future=q5 or "",
        q6_summary=q6 or "",
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
