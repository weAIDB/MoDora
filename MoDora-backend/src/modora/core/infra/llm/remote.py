from __future__ import annotations

import logging
import json
from pathlib import Path
from openai import AsyncOpenAI
from modora.core.settings import Settings
from modora.core.infra.llm.base import BaseAsyncLLMClient


class AsyncRemoteLLMClient(BaseAsyncLLMClient):
    def __init__(self, settings: Settings | None = None):
        super().__init__(settings)
        self._init_client()

    def _init_client(self):
        self.api_key = getattr(self.settings, "api_key", None)
        self.base_url = getattr(self.settings, "api_base", None)
        self.model = "gemini-2.5-flash" 
        
        # If not in settings, try manual load (fallback)
        if not self.api_key or not self.base_url:
            try:
                config_path = Path(__file__).parents[4] / "configs" / "local.json" # Adjust path if needed
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = json.load(f)
                        self.api_key = config.get("api_key")
                        self.base_url = config.get("api_base")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to load local.json manually: {e}")

        if not self.api_key or not self.base_url:
            # Instead of raising error immediately, we can log warning.
            # But strictly speaking, a client without config is useless.
            # However, for Factory pattern, we might want to defer this check or let Factory handle it.
            # Keeping it as is for now.
            # raise ValueError("api_key or api_base not found in settings or local.json")
            pass

        if self.api_key and self.base_url:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None

    async def _call_llm(self, prompt: str, base64_image: str | None = None) -> str:
        """
        Implementation of the abstract method to call remote LLM.
        """
        if not self.client:
             logging.getLogger(__name__).error("Remote LLM client not initialized (missing api_key/api_base)")
             return ""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        if base64_image:
            messages[0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    },
                }
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=2048,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logging.getLogger(__name__).error(f"Remote LLM call failed: {e}")
            return ""

    # Renaming for compatibility if needed, but BaseAsyncLLMClient defines _call_llm.
    # The original _call_remote_llm is now _call_llm.
    async def _call_remote_llm(self, prompt: str, base64_image: str | None = None) -> str:
         return await self._call_llm(prompt, base64_image)
