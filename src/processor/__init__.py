"""处理器模块"""

from .data_collector import collect_paper_data
from .summary_gen import SummaryGenerator, generate_summary

__all__ = ["collect_paper_data", "SummaryGenerator", "generate_summary"]
