"""数据收集器 - 并行获取论文相关信息"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..api.arxiv import ArxivPaper, fetch_arxiv_metadata
from ..api.papers_cool import KimiSummary, fetch_kimi_summary
from ..config import get_config
from ..crawler.pdf import download_pdf, extract_pdf_text


@dataclass
class PaperData:
    """论文完整数据"""

    paper_id: str
    arxiv_paper: Optional[ArxivPaper]
    kimi_summary: Optional[KimiSummary]
    local_comment: str
    pdf_text: str
    pdf_path: Optional[str]

    @property
    def title(self) -> str:
        return self.arxiv_paper.title if self.arxiv_paper else ""

    @property
    def authors(self) -> str:
        return self.arxiv_paper.authors if self.arxiv_paper else ""

    @property
    def original_abstract(self) -> str:
        return self.arxiv_paper.abstract if self.arxiv_paper else ""


def load_local_comment(paper_id: str) -> str:
    """加载本地评论文件"""
    config = get_config()
    comments_dir = Path(config.paths.comments_dir)
    comment_file = comments_dir / f"{paper_id}.md"

    if comment_file.exists():
        return comment_file.read_text(encoding="utf-8")

    return ""


async def collect_paper_data(
    paper_id: str, download: bool = True, force_download: bool = False
) -> PaperData:
    """并行收集论文相关数据"""
    config = get_config()

    pdf_path = None
    pdf_text = ""

    arxiv_data = None
    kimi_data = None

    def fetch_arxiv():
        try:
            return fetch_arxiv_metadata(paper_id)
        except Exception as e:
            print(f"Failed to fetch arXiv metadata: {e}")
            return None

    def fetch_kimi():
        try:
            return fetch_kimi_summary(paper_id)
        except Exception as e:
            print(f"Failed to fetch Kimi summary: {e}")
            return None

    arxiv_task = asyncio.to_thread(fetch_arxiv)
    kimi_task = asyncio.to_thread(fetch_kimi)

    arxiv_data, kimi_data = await asyncio.gather(arxiv_task, kimi_task)

    local_comment = load_local_comment(paper_id)

    if download and arxiv_data:
        pdf_dir = Path(config.paths.pdf_dir)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = str(pdf_dir / f"{paper_id}.pdf")

        if force_download or not Path(pdf_path).exists():
            try:
                download_pdf(paper_id, pdf_path)
            except Exception as e:
                print(f"Failed to download PDF: {e}")
                pdf_path = None

    if pdf_path and Path(pdf_path).exists():
        try:
            pdf_text = extract_pdf_text(pdf_path)
        except Exception as e:
            print(f"Failed to extract PDF text: {e}")

    return PaperData(
        paper_id=paper_id,
        arxiv_paper=arxiv_data,
        kimi_summary=kimi_data,
        local_comment=local_comment,
        pdf_text=pdf_text,
        pdf_path=pdf_path,
    )
