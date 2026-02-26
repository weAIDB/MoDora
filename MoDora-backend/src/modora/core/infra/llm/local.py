from __future__ import annotations

import logging
import threading
from typing import Any
from openai import AsyncOpenAI

from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.infra.llm.process import _resolve_model_path
from modora.core.settings import Settings


class AsyncLocalLLMClient(BaseAsyncLLMClient):
    """Asynchronous local LLM client, inherited from BaseAsyncLLMClient.

    Supports local multi-instance polling load balancing, while also compatible with
    external APIs via API Key and Base URL.
    """

    _rr_lock = threading.Lock()
    _rr_idx = 0
    _logger = logging.getLogger(__name__)

    def __init__(self, settings: Settings | None = None, instance_id: str | None = None):
        """Initialize local client.

        Args:
            settings: Configuration object. If None, default configuration is loaded.
            instance_id: Optional specific model instance ID to use.
        """
        super().__init__(settings, instance_id=instance_id)

    def _list_base_urls(self) -> list[str]:
        """Get a list of all available Base URLs."""
        # 1. If an explicit instance is provided, use its base_url or port
        if self.instance_id:
            instance = self.settings.resolve_model_instance(self.instance_id)
            if instance and instance.type == "local":
                if instance.base_url:
                    return [instance.base_url.rstrip("/")]
                if instance.port:
                    return [f"http://127.0.0.1:{instance.port}/v1"]

        # 2. Fallback to all local model_instances if no explicit instance_id or if it fails
        urls: list[str] = []
        for inst in self.settings.model_instances.values():
            if inst.type == "local":
                if inst.base_url:
                    urls.append(inst.base_url.rstrip("/"))
                elif inst.port:
                    urls.append(f"http://127.0.0.1:{inst.port}/v1")
        
        if urls:
            return urls

        # 3. Last resort fallback
        return ["http://127.0.0.1:9001/v1"]

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
                # Only process if img looks like Base64 (no spaces and sufficient length)
                if isinstance(img, str) and len(img) > 100 and " " not in img:
                    img = img.strip()
                    padding = len(img) % 4
                    if padding > 0:
                        img += "=" * (4 - padding)

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
        model = None
        if self.instance_id:
            instance = self.settings.resolve_model_instance(self.instance_id)
            if instance:
                model = instance.model
        
        if not model:
            # Fallback to the first local model found
            for inst in self.settings.model_instances.values():
                if inst.type == "local" and inst.model:
                    model = inst.model
                    break
        
        if not model:
            raise RuntimeError("No local model instance found in configuration")

        model = _resolve_model_path(model)
        self._logger.info(
            "local llm request model resolved",
            extra={
                "instance_id": self.instance_id,
                "model": model,
                "base_urls": self._list_base_urls(),
            },
        )
        base_urls = self._list_base_urls()
        start = self._get_next_start_index(len(base_urls))
        messages = self._create_messages(prompt, base64_image)

        api_key = "sk-no-key"
        if self.instance_id:
            instance = self.settings.resolve_model_instance(self.instance_id)
            if instance and instance.api_key:
                api_key = instance.api_key

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
