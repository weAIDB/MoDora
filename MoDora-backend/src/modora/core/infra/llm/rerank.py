from __future__ import annotations

import logging
from typing import List

from modora.core.infra.llm.base import _build_headers, _normalize_endpoint, _post_json
from modora.core.settings import Settings

logger = logging.getLogger(__name__)


class AsyncRerankClient:
    def __init__(
        self,
        settings: Settings | None = None,
    ):
        self.settings = settings or Settings()
        self.rerank_api_base = self.settings.rerank_api_base
        self.rerank_api_key = self.settings.rerank_api_key
        self.rerank_model_name = self.settings.rerank_model_name

    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        Rerank documents using OpenAI-compatible Rerank API.
        Returns a list of scores corresponding to the input documents.
        Raises exception if API call fails.
        """
        if not documents:
            return []

        if not self.rerank_api_base or not self.rerank_model_name:
            raise ValueError("Rerank API base or model name not configured")
        if not self.rerank_api_key:
            raise ValueError("Rerank API key not configured")

        url = _normalize_endpoint(self.rerank_api_base, "rerank")
        headers = _build_headers(self.rerank_api_key)

        payload = {
            "model": self.rerank_model_name,
            "query": query,
            "top_n": len(documents),
            "documents": documents,
        }

        data = await _post_json(url, payload=payload, headers=headers, timeout=30.0)

        # Parse results
        # Expecting: {"results": [{"index": int, "relevance_score": float}, ...]}
        if "results" not in data:
            raise ValueError(f"Unexpected rerank API response format: {data}")

        results = data["results"]
        # Create a score map: index -> score
        score_map = {item["index"]: item["relevance_score"] for item in results}

        # Return scores in order of input documents
        # If a document didn't get a score (unlikely), default to 0.0
        return [score_map.get(i, 0.0) for i in range(len(documents))]
