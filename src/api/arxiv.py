"""arXiv API客户端"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from xml.etree import ElementTree as ET

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..config import get_config


@dataclass
class ArxivPaper:
    id: str
    title: str
    authors: str
    abstract: str
    published: str
    updated: str
    pdf_url: str
    subjects: list[str]
    doi: Optional[str] = None
    journal_ref: Optional[str] = None

    @property
    def arxiv_url(self) -> str:
        return f"https://arxiv.org/abs/{self.id}"

    @property
    def tags(self) -> str:
        return ", ".join(self.subjects[:3])


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=30),
    retry=retry_if_exception_type(
        (requests.ConnectionError, requests.Timeout, requests.HTTPError)
    ),
)
def fetch_arxiv_metadata(paper_id: str) -> ArxivPaper:
    """获取arXiv论文元数据"""
    config = get_config()
    url = f"{config.arxiv.api_url}?id_list={paper_id}"

    headers = {"User-Agent": config.arxiv.user_agent}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    ATOM_NS = "http://www.w3.org/2005/Atom"
    ARXIV_NS = "http://arxiv.org/schemas/atom"

    entry = root.find(f"{{{ATOM_NS}}}entry")
    if entry is None:
        raise ValueError(f"Paper {paper_id} not found")

    def get_text(element, path):
        el = element.find(path)
        return el.text.strip() if el is not None and el.text else ""

    id_text = get_text(entry, f"{{{ATOM_NS}}}id")
    arxiv_id = id_text.split("/abs/")[-1] if "/abs/" in id_text else id_text

    title = get_text(entry, f"{{{ATOM_NS}}}title").replace("\n", " ").strip()

    authors = []
    for author in entry.findall(f"{{{ATOM_NS}}}author"):
        name = get_text(author, f"{{{ATOM_NS}}}name")
        authors.append(name)
    authors_str = ", ".join(authors)

    abstract = get_text(entry, f"{{{ATOM_NS}}}summary").replace("\n", " ").strip()

    published = get_text(entry, f"{{{ATOM_NS}}}published")
    updated = get_text(entry, f"{{{ATOM_NS}}}updated")

    pdf_url = ""
    for link in entry.findall(f"{{{ATOM_NS}}}link"):
        if link.get("title") == "pdf" or link.get("type") == "application/pdf":
            pdf_url = link.get("href", "")
            break

    subjects = []
    for subject in entry.findall(f"{{{ATOM_NS}}}category"):
        term = subject.get("term", "")
        subjects.append(term)

    doi_el = entry.find(f"{{{ARXIV_NS}}}doi")
    doi = doi_el.text.strip() if doi_el is not None and doi_el.text else ""
    journal_el = entry.find(f"{{{ARXIV_NS}}}journal_ref")
    journal_ref = (
        journal_el.text.strip() if journal_el is not None and journal_el.text else ""
    )

    return ArxivPaper(
        id=arxiv_id,
        title=title,
        authors=authors_str,
        abstract=abstract,
        published=published,
        updated=updated,
        pdf_url=pdf_url,
        subjects=subjects,
        doi=doi or None,
        journal_ref=journal_ref or None,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type(
        (requests.ConnectionError, requests.Timeout, requests.HTTPError)
    ),
)
def download_arxiv_pdf(paper_id: str, save_path: str) -> str:
    """下载arXiv PDF"""
    config = get_config()
    pdf_url = config.arxiv.pdf_url.format(id=paper_id)

    headers = {"User-Agent": config.arxiv.user_agent}

    response = requests.get(pdf_url, headers=headers, timeout=120, stream=True)
    response.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return save_path
