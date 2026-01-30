import json
import logging
from typing import Any

from modora.core.domain.cctree import CCTree
from modora.core.infra.llm.qwen import AsyncQwenLLMClient
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.services.retriever import AsyncRetriever
from modora.core.settings import Settings


class QAService:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.llm = AsyncQwenLLMClient()
        self.cropper = PDFCropper()
        self.retriever = AsyncRetriever(self.llm, self.cropper, logger)

    async def answer_question(
        self,
        query: str,
        cctree: CCTree,
        source_path: str,
        question_id: str | int = "N/A",
    ) -> dict[str, Any]:
        """
        回答问题，返回答案和证据。
        """
        # 1. 检索
        self.logger.info(
            f"Retrieving evidence for query: {query}", extra={"question_id": question_id}
        )
        retrieved_text, retrieved_bbox, trace = await self.retriever.retrieve(
            query, cctree, source_path, question_id
        )

        # 2. 准备证据
        full_evidence = list(retrieved_text.values())
        full_locations = []
        for bbox_list in retrieved_bbox.values():
            if isinstance(bbox_list, list):
                full_locations.extend(bbox_list)

        # 3. 推理生成答案
        answer = "None"
        try:
            schema = self._get_tree_schema(cctree.root.children) if cctree.root else {}

            if full_evidence:
                evidence_str = "\n".join(full_evidence)
                # 简化 schema 显示，避免 token 爆炸
                schema_str = json.dumps(schema, ensure_ascii=False)[:2000]
                answer = await self.llm.reason_retrieved(
                    query, schema_str, evidence_str
                )
            else:
                answer = "No relevant information found."
        except Exception as e:
            self.logger.error(
                f"Reasoning failed: {e}", extra={"question_id": question_id}
            )
            answer = "Error generating answer."

        # 4. 答案校验
        try:
            if not await self.llm.check_answer(query, answer):
                # 兜底逻辑：全文档推理（简化版，只传结构）
                simplified_tree = (
                    self._simplify_tree(cctree.root) if cctree.root else {}
                )
                tree_str = json.dumps(simplified_tree, ensure_ascii=False)[:30000]
                self.logger.warning(
                    "Answer check failed, falling back to whole document reasoning.",
                    extra={"question_id": question_id, "len": len(tree_str)},
                )
                answer = await self.llm.reason_whole(query, tree_str)
        except Exception as e:
            self.logger.error(
                f"Answer check/fallback failed: {e}", extra={"question_id": question_id}
            )

        # 5. 构造返回结果
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
            "retrieved_documents": display_documents[:5],  # Top 5 distinct pages
            "retrieval_trace": trace,
        }

    def _get_tree_schema(self, children: dict) -> dict:
        schema = {}
        for key, node in children.items():
            # Skip supplements to reduce noise
            if key == "Supplement":
                continue
            if node.children:
                schema[key] = self._get_tree_schema(node.children)
            else:
                schema[key] = "Leaf"
        return schema

    def _simplify_tree(self, node) -> dict:
        """递归简化树结构用于兜底推理"""
        simple = {
            "type": getattr(node, "type", "unknown"),
            "data": getattr(node, "data", "")
        }
        if node.children:
            simple["children"] = {
                k: self._simplify_tree(v) for k, v in node.children.items()
            }
        return simple
