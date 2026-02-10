from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from modora.core.domain.cctree import CCTree
from modora.core.services.qa_service import QAService as CoreQAService
from modora.core.settings import Settings


class QAService:
    def __init__(self, settings: Settings, logger: logging.Logger, llm_mode: str | None = None):
        self.settings = settings
        self.logger = logger
        self._core = CoreQAService(settings)

    async def answer_question(
        self,
        query: str,
        cctree: CCTree,
        source_path: str,
        question_id: str | int = "N/A",
    ) -> dict[str, Any]:
        result = await self._core.qa(cctree, query, source_path)
        retrieved_docs = result.get("retrieved_documents", [])
        display_documents = []
        seen_pages = set()
        for doc in retrieved_docs:
            page = doc.get("page", 0)
            if page in seen_pages:
                continue
            seen_pages.add(page)
            display_documents.append(
                {
                    "page": page,
                    "content": doc.get("content", ""),
                    "bboxes": doc.get("bboxes", []),
                }
            )

        return {
            "answer": result.get("answer", "No answer"),
            "retrieved_documents": display_documents[:5],
            "retrieval_trace": result.get("retrieval_trace", []),
        }
