from __future__ import annotations

import threading
from typing import Any
from openai import AsyncOpenAI

from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.settings import Settings


class AsyncLocalLLMClient(BaseAsyncLLMClient):
    """Asynchronous local LLM client, inherited from BaseAsyncLLMClient.

    Supports local multi-instance polling load balancing, while also compatible with
    external APIs via API Key and Base URL.
    """

    _rr_lock = threading.Lock()
    _rr_idx = 0

    def __init__(self, settings: Settings | None = None):
        super().__init__(settings)

    def _list_base_urls(self) -> list[str]:
        """Get a list of all available Base URLs."""
        # 1. Prioritize using explicitly configured llm_local_base_url
        if self.settings.llm_local_base_url:
            return [self.settings.llm_local_base_url.rstrip("/")]

        # 2. Then use local multi-instance configuration
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

        # 3. Fallback to default local port
        return [f"http://127.0.0.1:{self.settings.llm_local_port}/v1"]

    def _get_next_start_index(self, n: int) -> int:
        """Get the next starting index for round-robin."""
        if n <= 1:
            return 0
        with self._rr_lock:
            idx = AsyncLocalLLMClient._rr_idx % n
            AsyncLocalLLMClient._rr_idx += 1
            return idx

    def _create_messages(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Build message list in OpenAI format."""
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
        """Core implementation for calling LLM.

        Supports multi-instance round-robin and external API compatibility.
        """
        model = self.settings.llm_local_model
        if not model:
            raise RuntimeError("llm_local_model is not configured")

        base_urls = self._list_base_urls()
        start = self._get_next_start_index(len(base_urls))
        messages = self._create_messages(prompt, base64_image)

        # Prioritize using locally configured API Key
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
