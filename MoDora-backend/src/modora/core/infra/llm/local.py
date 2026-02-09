from __future__ import annotations

import threading
from typing import Any
from openai import AsyncOpenAI

from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.settings import Settings


class AsyncLocalLLMClient(BaseAsyncLLMClient):
    """
    异步本地 LLM 客户端，继承自 BaseAsyncLLMClient。
    支持本地多实例轮询负载均衡，同时兼容通过 API Key 和 Base URL 使用外部 API。
    """

    _rr_lock = threading.Lock()
    _rr_idx = 0

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings)

    def _list_base_urls(self) -> list[str]:
        """获取所有可用的 Base URL 列表。"""
        # 1. 优先使用显式配置的 llm_local_base_url
        if self.settings.llm_local_base_url:
            return [self.settings.llm_local_base_url.rstrip("/")]

        # 2. 其次使用本地多实例配置
        instances = list(getattr(self.settings, "llm_local_instances", ()) or ())
        if instances:
            urls: list[str] = []
            for it in instances:
                host = (getattr(it, "host", None) or "127.0.0.1").strip() or "127.0.0.1"
                port = int(
                    getattr(it, "port", self.settings.llm_local_port)
                    or self.settings.llm_local_port
                )
                urls.append(f"http://{host}:{port}/v1")
            return urls

        # 3. 回退到默认本地端口
        return [f"http://127.0.0.1:{self.settings.llm_local_port}/v1"]

    def _get_next_start_index(self, n: int) -> int:
        """获取轮询的下一个起始索引。"""
        if n <= 1:
            return 0
        with self._rr_lock:
            idx = AsyncLocalLLMClient._rr_idx % n
            AsyncLocalLLMClient._rr_idx += 1
            return idx

    def _create_messages(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> list[dict[str, Any]]:
        """构建 OpenAI 格式的消息列表。"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        if base64_image is not None:
            if isinstance(base64_image, str):
                base64_image = [base64_image]

            for img in base64_image:
                messages[0]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                    }
                )
        return messages

    async def _call_llm(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> str:
        """
        调用 LLM 的核心实现。支持多实例轮询和外部 API 兼容。
        """
        model = self.settings.llm_local_model
        if not model:
            raise RuntimeError("llm_local_model is not configured")

        base_urls = self._list_base_urls()
        start = self._get_next_start_index(len(base_urls))
        messages = self._create_messages(prompt, base64_image)

        # 优先使用本地配置的 API Key
        api_key = self.settings.llm_local_api_key or "sk-no-key"

        last_exc: Exception | None = None
        for i in range(len(base_urls)):
            base_url = base_urls[(start + i) % len(base_urls)]
            try:
                client = AsyncOpenAI(base_url=base_url, api_key=api_key)
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=8192,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                last_exc = e
                continue

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("No LLM endpoints configured or all endpoints failed")
