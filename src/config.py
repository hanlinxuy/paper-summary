"""配置文件加载器"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class TextAPISettings(BaseModel):
    """文本生成API配置"""

    provider: str = "siliconflow"
    base_url: str = "https://api.siliconFlow.cn/v1"
    model: str = "deepseek-ai/DeepSeek-V3.2"
    timeout: int = 120


class VLAPISettings(BaseModel):
    """图像/VL分析API配置"""

    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    timeout: int = 120


class APISettings(BaseModel):
    """API配置"""

    text: TextAPISettings = TextAPISettings()
    vl: VLAPISettings = VLAPISettings()
    api_key: Optional[str] = ""


class BrowserSettings(BaseModel):
    """Playwright/Browser配置"""

    enabled: bool = True
    headless: bool = True
    timeout: int = 30000
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    cache_enabled: bool = True
    cache_ttl: int = 86400
    cache_dir: str = "./cache/html"
    proxy: str = ""  # 代理地址，例如: "http://127.0.0.1:7890"


class FlexModeSettings(BaseModel):
    """灵活模式配置"""

    enabled: bool = False  # 默认禁用回退，只有 True 时才允许 API 回退
    arxiv_api: bool = True
    papers_cool_api: bool = False


class ArxivSettings(BaseModel):
    api_url: str = "http://export.arxiv.org/api/query"
    pdf_url: str = "https://arxiv.org/pdf/{id}.pdf"
    user_agent: str = "PaperSummaryBot/1.0"


class PapersCoolSettings(BaseModel):
    base_url: str = "https://papers.cool"
    kimi_endpoint: str = "/arxiv/kimi"
    timeout: int = 60


class PathsSettings(BaseModel):
    cache_dir: str = "./cache"
    pdf_dir: str = "./cache/pdfs"
    summaries_dir: str = "./cache/summaries"
    logs_dir: str = "./cache/logs"
    comments_dir: str = "./data/comments"
    templates_dir: str = "./templates"


class PDFSettings(BaseModel):
    max_pages: int = 0
    max_chars: int = 50000


class SummarySettings(BaseModel):
    template: str = "academic_summary.md.j2"
    temperature: float = 0.3
    max_tokens: int = 4096
    max_retries: int = 3
    # 生成模式: full / lightweight / two_phase
    mode: str = "full"
    # 是否在two_phase模式下启用PDF增强
    pdf_enhance_enabled: bool = True


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    api: APISettings = APISettings()
    browser: BrowserSettings = BrowserSettings()
    flex_mode: FlexModeSettings = FlexModeSettings()
    arxiv: ArxivSettings = ArxivSettings()
    papers_cool: PapersCoolSettings = PapersCoolSettings()
    paths: PathsSettings = PathsSettings()
    pdf: PDFSettings = PDFSettings()
    summary: SummarySettings = SummarySettings()
    logging: LoggingSettings = LoggingSettings()


def load_config(config_path: Optional[Path] = None) -> Config:
    """加载配置文件"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    config_data: Dict[str, Any] = {}

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    config = Config(**config_data)

    # 根据 provider 自动查找环境变量: {PROVIDER}_API_KEY
    def get_api_key(provider: str) -> Optional[str]:
        env_key = f"{provider.upper()}_API_KEY"
        return os.getenv(env_key)

    # 优先从环境变量获取 API key
    text_key = get_api_key(config.api.text.provider)
    if text_key:
        config.api.api_key = text_key
    else:
        vl_key = get_api_key(config.api.vl.provider)
        if vl_key:
            config.api.api_key = vl_key

    # 从环境变量读取代理配置（支持 HTTP_PROXY, HTTPS_PROXY）
    if not config.browser.proxy:
        config.browser.proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or ""

    return config


def get_config() -> Config:
    """获取全局配置"""
    return load_config()
