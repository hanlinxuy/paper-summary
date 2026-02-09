"""摘要生成器"""

import asyncio
from pathlib import Path

from ..config import get_config
from ..llm.client import LLMClient
from .data_collector import PaperData, collect_paper_data


class SummaryGenerator:
    """论文摘要生成器"""

    def __init__(self, api_key: str = ""):
        self.client = LLMClient(api_key) if api_key else LLMClient()
        self.config = get_config()

    async def generate(
        self,
        paper_id: str,
        download: bool = True,
        force: bool = False,
        use_pdf_llm: bool = True,
        temp_comments: list[str] | None = None,
    ) -> str:
        """生成论文摘要"""
        data = await collect_paper_data(
            paper_id=paper_id, download=download, force_download=force
        )

        kimi_content = ""
        if data.kimi_summary:
            kimi_content = data.kimi_summary.extract_text_content()

        pdf_summary = ""
        if use_pdf_llm and data.pdf_path:
            try:
                from ..crawler.pdf import process_pdf

                loop = asyncio.get_event_loop()
                pdf_summary = await loop.run_in_executor(
                    None, lambda: process_pdf(Path(data.pdf_path), use_direct_llm=False)
                )
            except Exception as e:
                print(f"Failed to process PDF: {e}")

        # 合并文件评论和临时评论
        local_comment = self._merge_comments(data.local_comment, temp_comments or [])

        summary = self.client.generate_academic_summary(
            paper_id=data.paper_id,
            title=data.title,
            authors=data.authors,
            original_abstract=data.original_abstract,
            kimi_summary=kimi_content,
            local_comment=local_comment,
            pdf_summary=pdf_summary,
        )

        self._save_summary(data.paper_id, summary)

        return summary

    def _merge_comments(self, file_comment: str, temp_comments: list[str]) -> str:
        """合并文件评论和临时评论"""
        parts = []
        if file_comment:
            parts.append(file_comment)
        if temp_comments:
            parts.extend(temp_comments)
        return "\n\n".join(parts) if parts else ""

    def _save_summary(self, paper_id: str, summary: str):
        """保存摘要到文件"""
        summaries_dir = Path(self.config.paths.summaries_dir)
        summaries_dir.mkdir(parents=True, exist_ok=True)

        output_path = summaries_dir / f"{paper_id}_summary.md"
        output_path.write_text(summary, encoding="utf-8")

        print(f"Summary saved to: {output_path}")


async def generate_summary(
    paper_id: str,
    download: bool = True,
    force: bool = False,
    use_pdf_llm: bool = True,
    temp_comments: list[str] | None = None,
) -> str:
    """生成摘要 - 便捷函数"""
    generator = SummaryGenerator()
    return await generator.generate(
        paper_id=paper_id,
        download=download,
        force=force,
        use_pdf_llm=use_pdf_llm,
        temp_comments=temp_comments,
    )
