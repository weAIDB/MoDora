from __future__ import annotations

import logging
from typing import List, Union

from modora.core.infra.llm.base import _build_headers, _normalize_endpoint, _post_json
from modora.core.settings import Settings

logger = logging.getLogger(__name__)


class AsyncEmbeddingClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.embedding_api_key = self.settings.embedding_api_key
        self.embedding_api_base = self.settings.embedding_api_base
        self.embedding_model_name = (
            self.settings.embedding_model_name or "text-embedding-3-large"
        )

    async def embed(self, text: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(text, str):
            text = [text]

        if not self.embedding_api_base:
            raise ValueError("Embedding API base URL not configured")
        if not self.embedding_api_key:
            raise ValueError("Embedding API key not configured")

        url = _normalize_endpoint(self.embedding_api_base, "embeddings")
        headers = _build_headers(self.embedding_api_key)

        payload = {
            "model": self.embedding_model_name,
            "input": text,
        }

        try:
            data = await _post_json(url, payload=payload, headers=headers, timeout=60.0)
            if "data" not in data:
                raise ValueError(f"Unexpected embedding API response format: {data}")

            results = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in results]

        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            raise

    async def get_embedding(self, text: Union[str, List[str]]) -> List[List[float]]:
        return await self.embed(text)
