"""Paper Summary - 论文摘要生成器"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.yaml"
CACHE_DIR = BASE_DIR / "cache"
PDF_DIR = CACHE_DIR / "pdfs"
SUMMARIES_DIR = CACHE_DIR / "summaries"
LOGS_DIR = CACHE_DIR / "logs"
COMMENTS_DIR = BASE_DIR / "data" / "comments"
TEMPLATES_DIR = BASE_DIR / "templates"

__version__ = "0.1.0"
