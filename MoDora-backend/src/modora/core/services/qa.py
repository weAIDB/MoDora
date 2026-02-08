import json
import logging
from typing import Any

from modora.core.domain.cctree import CCTree
from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.prompts.retrieval import (
    image_reasoning_prompt,
    whole_reasoning_prompt,
)
from modora.core.services.retriever_factory import RetrieverFactory
from modora.core.settings import Settings


class QAService:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        # Use Factory to create LLM client
        self.llm = AsyncLLMFactory.create(settings, mode="local")
        # Create a dedicated remote client for reasoning steps
        self.remote_llm = AsyncLLMFactory.create(settings, mode="local")
        
        self.cropper = PDFCropper()
        # Use the Factory to create retriever
        self.retriever = RetrieverFactory.create(settings, logger, strategy="fast_location")

    async def answer_question(
        self,
        query: str,
        cctree: CCTree,
        source_path: str,
        question_id: str | int = "N/A",
    ) -> dict[str, Any]:
        """
        回答问题，返回答案和证据。
        添加全局重试机制：如果答案校验失败，重新检索并生成，最多重试 3 次。
        """
        max_attempts = 3
        last_result = {}

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                self.logger.warning(
                    f"Retry answer generation (attempt {attempt}/{max_attempts})",
                    extra={"question_id": question_id},
                )

            # 1. 检索
            self.logger.info(
                f"Retrieving evidence for query: {query}", extra={"question_id": question_id}
            )
            retrieved_text, retrieved_bbox, retrieved_images, trace = await self.retriever.retrieve(
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
            reasoning_prompt = ""
            fallback_prompt = ""
            debug_images = []
            
            try:
                schema = self._get_tree_schema(cctree.root.children) if cctree.root else {}

                if full_evidence:
                    # Truncate evidence to prevent token overflow (approx 10k chars)
                    evidence_str = "\n".join(full_evidence)
                    if len(evidence_str) > 10000:
                        evidence_str = evidence_str[:10000] + "...(truncated)"
                    
                    # 简化 schema 显示，避免 token 爆炸 (approx 5k chars)
                    schema_str = json.dumps(schema, ensure_ascii=False)[:5000]
                    
                    # Capture the full prompt context for debugging
                    reasoning_prompt = image_reasoning_prompt.format(
                        query=query, schema=schema_str, evidence=evidence_str
                    )
                    
                    # Use remote LLM for reasoning
                    images_list = list(retrieved_images.values())
                    
                    # Limit the number of images to prevent INPUT_LENGTH_ERROR (Stricter limit)
                    max_images = 3
                    if len(images_list) > max_images:
                        self.logger.warning(
                            f"Too many images retrieved ({len(images_list)}), truncating to {max_images}",
                            extra={"question_id": question_id}
                        )
                        images_list = images_list[:max_images]
                    
                    debug_images = images_list

                    answer = await self.remote_llm.reason_retrieved(
                        query, schema_str, evidence_str, images=images_list
                    )
                else:
                    answer = "No relevant information found."
            except Exception as e:
                self.logger.error(
                    f"Reasoning failed: {e}", extra={"question_id": question_id}
                )
                answer = "Error generating answer."

            # 4. 答案校验
            check_passed = False
            try:
                # Use remote LLM for answer check
                if await self.remote_llm.check_answer(query, answer):
                    check_passed = True
            except Exception as e:
                self.logger.error(
                    f"Answer check failed: {e}", extra={"question_id": question_id}
                )
                check_passed = False

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

            last_result = {
                "answer": answer,
                "retrieved_documents": display_documents,
                "retrieval_trace": trace,
                "debug_prompts": {
                    "reasoning_context": reasoning_prompt,
                    "fallback_context": fallback_prompt,
                    "images": debug_images,
                }
            }

            if check_passed:
                return last_result
            
            # 如果没通过校验且还有重试机会，循环继续（重新检索）
            # 注意：这里的重新检索依赖于 retrieve 方法本身是否有随机性或者
            # 是否有状态更新。如果 retrieve 是确定性的，重试可能得到相同结果。
            # 通常 LLM 的检索或生成有一定随机性 (temperature > 0)。

        # 如果重试次数用完仍未通过，尝试最终的全文档兜底
        self.logger.warning(
            f"Failed to generate valid answer after {max_attempts} attempts. Falling back to whole document reasoning.",
            extra={"question_id": question_id},
        )
        
        try:
             # 兜底逻辑：全文档推理
            tree_str = json.dumps(cctree.root.to_dict(), ensure_ascii=False)[:15000]
            
            # Capture fallback prompt
            fallback_prompt = whole_reasoning_prompt.format(
                query=query, data=tree_str
            )
            last_result["debug_prompts"]["fallback_context"] = fallback_prompt
            
            # Use remote LLM for whole document reasoning
            answer = await self.remote_llm.reason_whole(query, tree_str)
            
            # 更新最后的结果
            last_result["answer"] = answer
            last_result["debug_prompts"]["fallback_context"] = fallback_prompt
            
            # 对兜底结果进行最终校验（可选，为了记录日志）
            is_valid = await self.remote_llm.check_answer(query, answer)
            if not is_valid:
                 self.logger.warning("Whole document reasoning also failed validation.", extra={"question_id": question_id})

        except Exception as e:
            self.logger.error(
                f"Final fallback failed: {e}", extra={"question_id": question_id}
            )
            last_result["answer"] = "Failed to generate answer even after fallback."

        return last_result

    def _get_tree_schema(self, children: dict) -> dict:
        schema = {}
        for key, node in children.items():
            # Skip supplements to reduce noise
            if key == "Supplement":
                continue
            if node.children:
                schema[key] = self._get_tree_schema(node.children)
        return schema

    def _simplify_tree(self, node) -> dict:
        """递归简化树结构用于兜底推理"""
        simple = {
            "type": getattr(node, "type", "unknown"),
            "data": getattr(node, "data", "")[:100]
        }
        if node.children:
            simple["children"] = {
                k: self._simplify_tree(v) for k, v in node.children.items()
            }
        return simple
