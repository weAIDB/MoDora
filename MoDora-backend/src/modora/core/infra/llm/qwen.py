from __future__ import annotations

import re
import threading
from typing import Tuple

from openai import AsyncOpenAI, OpenAI

from modora.core.interfaces.llm import LLMClient
from modora.core.prompts.enrichment import (
    chart_enrichment_prompt,
    image_enrichment_prompt,
    table_enrichment_prompt,
)
from modora.core.prompts.hierarchy import level_title_prompt
from modora.core.prompts.metadata import (
    metadata_generation_prompt,
    metadata_integration_prompt,
)
from modora.core.prompts.retrieval import (
    question_parsing_prompt,
    select_children_prompt,
    check_node_prompt1,
    check_node_prompt2,
    check_answer_prompt,
    retrieved_reasoning_prompt,
    whole_reasoning_prompt,
)
from modora.core.settings import Settings

_rr_lock = threading.Lock()
_rr_idx = 0


def _prompt_for_type(cp_type: str) -> str:
    """根据组件类型选择对应的 enrichment prompt。"""
    t = (cp_type or "").strip().lower()
    if t == "table":
        return table_enrichment_prompt
    if t == "chart":
        return chart_enrichment_prompt
    return image_enrichment_prompt


def _list_base_urls(settings: Settings) -> list[str]:
    instances = list(getattr(settings, "llm_local_instances", ()) or ())
    if instances:
        urls: list[str] = []
        for it in instances:
            host = (getattr(it, "host", None) or "127.0.0.1").strip() or "127.0.0.1"
            port = int(
                getattr(it, "port", settings.llm_local_port) or settings.llm_local_port
            )
            urls.append(f"http://{host}:{port}/v1")
        return urls
    return [f"http://127.0.0.1:{settings.llm_local_port}/v1"]


def _next_rr(n: int) -> int:
    global _rr_idx
    if n <= 1:
        return 0
    with _rr_lock:
        idx = _rr_idx % n
        _rr_idx += 1
        return idx


def _create_messages(prompt: str, base64_image: str | None = None) -> list:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
            ],
        }
    ]
    if base64_image is not None:
        messages[0]["content"].append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"  # 使用Base64数据
                },
            }
        )
    return messages


def call_qwen_vl(
    prompt: str, base64_image: str | None = None, settings: Settings | None = None
) -> str:
    """通过 OpenAI 兼容接口调用本地 Qwen-VL（lmdeploy api_server）。"""
    settings = settings or Settings.load()
    if not settings.llm_local_model:
        raise RuntimeError("llm_local_model is not configured")

    base_urls = _list_base_urls(settings)
    start = _next_rr(len(base_urls))
    messages = _create_messages(prompt, base64_image)

    last_exc: Exception | None = None
    for i in range(len(base_urls)):
        base_url = base_urls[(start + i) % len(base_urls)]
        try:
            client = OpenAI(base_url=base_url, api_key="local")
            response = client.chat.completions.create(
                model=settings.llm_local_model,
                messages=messages,
                max_completion_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_exc = e
            continue

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("no llm endpoints configured")


async def call_qwen_vl_async(
    prompt: str, base64_image: str | None = None, settings: Settings | None = None
) -> str:
    settings = settings or Settings.load()
    if not settings.llm_local_model:
        raise RuntimeError("llm_local_model is not configured")

    base_urls = _list_base_urls(settings)
    start = _next_rr(len(base_urls))
    messages = _create_messages(prompt, base64_image)

    last_exc: Exception | None = None
    for i in range(len(base_urls)):
        base_url = base_urls[(start + i) % len(base_urls)]
        try:
            client = AsyncOpenAI(base_url=base_url, api_key="local")
            response = await client.chat.completions.create(
                model=settings.llm_local_model,
                messages=messages,
                max_completion_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_exc = e
            continue

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("no llm endpoints configured")


def qwen_annotation(
    base64_image: str, cp_type: str, settings: Settings | None = None
) -> tuple[str, str, str]:
    """对图片进行标注，按 [T][M][C] 结构解析标题/元数据/内容。"""
    prompt = _prompt_for_type(cp_type)
    pattern = re.compile(r"\[T\](.*?)\[M\](.*?)\[C\](.*)", re.DOTALL)

    title = "Default Title"
    metadata = "Default Metadata"
    content = "Default Content"

    settings = settings or Settings.load()
    for _ in range(3):
        text = call_qwen_vl(prompt, base64_image, settings=settings) or ""
        m = pattern.search(text)
        if m:
            title = m.group(1).strip() or title
            metadata = m.group(2).strip() or metadata
            content = m.group(3).strip() or content
            break

    return title, metadata, content


class QwenLLMClient(LLMClient):
    """
    Qwen LLM 客户端适配器。
    实现了 LLMClient 接口，底层调用本地部署的 Qwen-VL 模型。
    """

    def generate_annotation(
        self, base64_image: str, cp_type: str
    ) -> Tuple[str, str, str]:
        """
        调用 Qwen 模型生成图片标注。

        Args:
            base64_image: Base64 编码的图片
            cp_type: 组件类型

        Returns:
            Tuple[str, str, str]: (标题, 元数据, 内容)
        """
        return qwen_annotation(base64_image, cp_type)

    def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        """
        调用 Qwen 模型生成标题层次结构。

        Args:
            title_list: 标题列表
            base64_image: Base64 编码的图片

        Returns:
            str: 标题层次结构
        """
        prompt = level_title_prompt.format(raw_list=title_list)
        leveled_title = call_qwen_vl(prompt, base64_image) or ""
        return leveled_title


def _bool_string(s: str) -> bool:
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False


from modora.core.infra.llm.base import BaseAsyncLLMClient

class AsyncQwenLLMClient(BaseAsyncLLMClient):
    """
    Async Qwen LLM Client inheriting from BaseAsyncLLMClient.
    Uses call_qwen_vl_async for the underlying LLM call.
    """
    async def _call_llm(self, prompt: str, base64_image: str | None = None) -> str:
        return await call_qwen_vl_async(prompt, base64_image, settings=self.settings)

