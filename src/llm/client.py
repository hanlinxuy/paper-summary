"""LLM客户端 - 支持混合服务商（按功能区分）"""

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import requests
from jinja2 import Template
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import get_config
from .prompt import ACADEMIC_SUMMARY_PROMPT


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)


class LLMClient:
    """LLM客户端 - 支持混合服务商，按功能选择provider"""

    def __init__(self, api_key: Optional[str] = None):
        config = get_config()
        self.config = config

        if api_key:
            self.api_key = api_key
        else:
            self.api_key = config.api.api_key

        if not self.api_key:
            raise ValueError(
                "API key not configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY env var"
            )

    def _parse_response(self, provider: str, result: dict) -> str:
        if provider == "anthropic":
            content_parts = []
            for block in result.get("content", []):
                if block.get("type") == "text":
                    content_parts.append(block.get("text", ""))
                elif block.get("type") == "thinking":
                    continue
            return "\n".join(content_parts)
        else:
            return result["choices"][0]["message"]["content"]

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """发送聊天请求（文本生成）"""
        if temperature is None:
            temperature = self.config.summary.temperature
        if max_tokens is None:
            max_tokens = self.config.summary.max_tokens

        text_config = self.config.api.text
        provider = text_config.provider

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": text_config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if provider == "anthropic":
            url = f"{text_config.base_url}/messages"
            headers["anthropic-version"] = "2023-06-01"
            headers["anthropic-dangerous-direct-browser-access"] = "true"
        else:
            url = f"{text_config.base_url}/chat/completions"

        response = requests.post(
            url, headers=headers, json=payload, timeout=text_config.timeout
        )
        response.raise_for_status()

        result = response.json()
        content = self._parse_response(provider, result)
        usage = result.get("usage", {})

        return LLMResponse(content=content, model=text_config.model, usage=usage)

    def generate_academic_summary(
        self,
        paper_id: str,
        title: str,
        authors: str,
        original_abstract: str,
        kimi_summary: str,
        local_comment: str = "",
        pdf_summary: str = "",
    ) -> str:
        """生成学术摘要"""
        template = Template(ACADEMIC_SUMMARY_PROMPT)
        prompt = template.render(
            paper_id=paper_id,
            title=title,
            authors=authors,
            original_abstract=original_abstract or "未提供",
            kimi_summary=kimi_summary or "未提供",
            local_comment=local_comment or "无",
            pdf_summary=pdf_summary,
        )

        response = self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096,
        )

        return response.content

    def analyze_image(
        self,
        image_path: Union[str, Path],
        prompt: Optional[str] = None,
    ) -> str:
        """分析图片（使用VL API配置）"""
        vl_config = self.config.api.vl
        provider = vl_config.provider

        if prompt is None:
            prompt = (
                "请详细分析这张图片中的内容，包括图表、公式、实验结果等所有可见信息。"
            )

        base64_image = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": vl_config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        if provider == "anthropic":
            url = f"{vl_config.base_url}/messages"
            headers["anthropic-version"] = "2023-06-01"
            headers["anthropic-dangerous-direct-browser-access"] = "true"
        else:
            url = f"{vl_config.base_url}/chat/completions"

        response = requests.post(
            url, headers=headers, json=payload, timeout=vl_config.timeout
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]


def generate_summary(
    paper_id: str,
    title: str,
    authors: str,
    original_abstract: str,
    kimi_summary: str,
    local_comment: str = "",
    pdf_summary: str = "",
) -> str:
    """生成学术摘要 - 便捷函数"""
    client = LLMClient()
    return client.generate_academic_summary(
        paper_id=paper_id,
        title=title,
        authors=authors,
        original_abstract=original_abstract,
        kimi_summary=kimi_summary,
        local_comment=local_comment,
        pdf_summary=pdf_summary,
    )
