"""PDF处理模块"""

import re
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader

from ..config import get_config


def download_pdf(paper_id: str, save_path: str) -> str:
    """下载PDF文件"""
    from ..api.arxiv import download_arxiv_pdf

    return download_arxiv_pdf(paper_id, save_path)


def extract_pdf_text(pdf_path: str, max_pages: int = 0, max_chars: int = 50000) -> str:
    """提取PDF文本内容"""
    config = get_config()

    if max_pages == 0:
        max_pages = config.pdf.max_pages
    if max_chars == 0:
        max_chars = config.pdf.max_chars

    reader = PdfReader(pdf_path)
    text_parts = []

    pages_to_process = (
        min(len(reader.pages), max_pages) if max_pages > 0 else len(reader.pages)
    )

    for i, page in enumerate(reader.pages[:pages_to_process]):
        text = page.extract_text()
        if text:
            text_parts.append(f"[Page {i + 1}]\n{text}")

        if sum(len(part) for part in text_parts) >= max_chars:
            break

    full_text = "\n\n".join(text_parts)

    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n... (内容截断)"

    return full_text


def extract_key_sections(text: str) -> str:
    """提取论文关键部分（摘要、结论、方法等）"""
    sections = {"abstract": [], "introduction": [], "method": [], "conclusion": []}

    current_section = None

    for line in text.split("\n"):
        line_lower = line.lower().strip()

        if re.match(r"^\s*#+\s*\w+", line):
            if "abstract" in line_lower:
                current_section = "abstract"
            elif "intro" in line_lower:
                current_section = "introduction"
            elif re.match(r"^\s*#+\s*(method|approach|proposal)", line_lower):
                current_section = "method"
            elif "conclusion" in line_lower or "future" in line_lower:
                current_section = "conclusion"
            else:
                current_section = None
        elif current_section and len(line.strip()) > 50:
            sections[current_section].append(line.strip())

    result_parts = []

    if sections["abstract"]:
        result_parts.append("## 摘要")
        result_parts.append(" ".join(sections["abstract"][:5]))

    if sections["introduction"]:
        result_parts.append("\n## 引言")
        result_parts.append(" ".join(sections["introduction"][:10]))

    if sections["method"]:
        result_parts.append("\n## 方法")
        result_parts.append(" ".join(sections["method"][:15]))

    if sections["conclusion"]:
        result_parts.append("\n## 结论")
        result_parts.append(" ".join(sections["conclusion"][:10]))

    return "\n".join(result_parts)


async def process_pdf(pdf_path: Path, use_direct_llm: bool = True) -> str:
    """处理PDF - 优先直接LLM分析，回退提取文本"""
    from ..llm.client import LLMClient

    client = LLMClient()

    if use_direct_llm:
        try:
            return client.analyze_pdf_direct(pdf_path)
        except Exception as e:
            print(f"Direct PDF analysis failed: {e}, falling back to text extraction")

    return extract_key_sections(extract_pdf_text(str(pdf_path)))
