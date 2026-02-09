from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from modora.core.domain.cctree import CCTree
from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.services.retriever import AsyncRetriever
from modora.core.settings import Settings


class QAService:
    def __init__(self, settings: Settings, logger: logging.Logger, llm_mode: str | None = None):
        self.settings = settings
        self.logger = logger
        self.llm = AsyncLLMFactory.create(settings, mode=llm_mode)
        self.cropper = PDFCropper()
        self.retriever = AsyncRetriever(self.llm, self.cropper, logger)

    async def answer_question(
        self,
        query: str,
        cctree: CCTree,
        source_path: str,
        question_id: str | int = "N/A",
    ) -> dict[str, Any]:
        retrieved_text, retrieved_bbox, trace = await self.retriever.retrieve(
            query, cctree, source_path, question_id
        )

        full_evidence = list(retrieved_text.values())
        answer = "No relevant information found."
        try:
            schema = self._get_tree_schema(cctree.root.children) if cctree.root else {}
            if full_evidence:
                evidence_str = "\n".join(full_evidence)
                schema_str = str(schema)[:2000]
                answer = await self.llm.reason_retrieved(query, schema_str, evidence_str)
            else:
                answer = "No relevant information found."
        except Exception as e:
            self.logger.error(f"Reasoning failed: {e}", extra={"question_id": question_id})
            answer = "Error generating answer."

        try:
            if not await self.llm.check_answer(query, answer):
                simple_tree = self._simplify_tree(cctree.root) if cctree.root else {}
                answer = await self.llm.reason_whole(query, str(simple_tree)[:30000])
        except Exception as e:
            self.logger.error(f"Answer check failed: {e}", extra={"question_id": question_id})

        display_documents = []
        seen_pages = set()
        for path, bbox_list in retrieved_bbox.items():
            if not bbox_list:
                continue
            page = bbox_list[0].get("page", 0)
            if page in seen_pages:
                continue
            seen_pages.add(page)
            display_documents.append(
                {
                    "page": page,
                    "content": retrieved_text.get(path, ""),
                    "bboxes": bbox_list,
                }
            )

        return {
            "answer": answer,
            "retrieved_documents": display_documents[:5],
            "retrieval_trace": trace,
        }

    def _get_tree_schema(self, children: dict) -> dict:
        schema = {}
        for key, node in children.items():
            if key == "Supplement":
                continue
            if node.children:
                schema[key] = self._get_tree_schema(node.children)
            else:
                schema[key] = "Leaf"
        return schema

    def _simplify_tree(self, node) -> dict:
        simple = {
            "type": getattr(node, "type", "unknown"),
            "data": getattr(node, "data", ""),
        }
        if node.children:
            simple["children"] = {k: self._simplify_tree(v) for k, v in node.children.items()}
        return simple
