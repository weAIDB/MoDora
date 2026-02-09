import ast
import logging
from typing import Tuple, List

from modora.core.settings import Settings
from modora.core.domain import CCTree, RetrievalResult
from modora.core.infra.llm import AsyncLLMFactory
from modora.core.infra.pdf import PDFCropper
from modora.core.prompts import location_extraction_prompt
from modora.core.services.retrieve import LocationRetriever, SemanticRetriever

logger = logging.getLogger(__name__)


class QAService:
    """
    QA 服务类，负责协调检索、推理和验证流程。
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.local_llm = AsyncLLMFactory.create(self.settings, mode="local")
        self.remote_llm = AsyncLLMFactory.create(self.settings, mode="remote")
        self.cropper = PDFCropper()
        self.semantic_retriever = SemanticRetriever(self.settings)
        self.location_retriever = LocationRetriever()

    async def extract_location(self, query: str) -> Tuple[List[int], List[float]]:
        """
        从查询语句中提取位置信息（页码和坐标）。
        """
        prompt = location_extraction_prompt.format(query=query)
        response = await self.remote_llm.generate_text(prompt)
        try:
            # 预期格式: "Page: [<page1>, <page2>]; Position: [<row>, <column>]"
            page_numbers = response.split("Page:")[1].split(";")[0].strip()
            position = response.split("Position:")[1].strip()
            page_list = ast.literal_eval(page_numbers)
            position_vector = ast.literal_eval(position)
        except Exception as e:
            logger.warning(f"Error parsing location: {e}, Response: {response}")
            page_list = [-1]
            position_vector = [-1.0, -1.0]
        return page_list, position_vector

    async def qa(self, cctree: CCTree, query: str, source_path: str) -> dict:
        """
        执行完整的 QA 流程：提取位置 -> 检索 -> 推理 -> 验证/回退。
        """
        page_list, position_vector = await self.extract_location(query)

        result = RetrievalResult()

        # 1. 检索
        if -1 in page_list and position_vector == [-1.0, -1.0]:
            result = await self.semantic_retriever.retrieve(cctree, query, source_path)
        else:
            result = self.location_retriever.retrieve(
                cctree, page_list, position_vector, source_path
            )

        # 2. 处理结果并推理
        schema = cctree.get_structure()
        answer = "None"
        trace = [
            {
                "step": "extract_location",
                "page_list": page_list,
                "position_vector": position_vector,
            },
            {"step": "retrieve", "locations_count": len(result.locations)},
        ]

        try:
            if result.locations or result.text_map:
                # 根据精确位置裁剪图像
                # TODO: 按照页来分组裁剪
                images = self.cropper.crop_image(source_path, result.locations)

                answer = await self.remote_llm.reason_retrieved(
                    query=query,
                    evidence=str(result.text_map),
                    images=images,
                    schema=str(schema),
                )
            else:
                answer = "None"

        except Exception as e:
            logger.error(f"Error in reasoning: {e}", exc_info=True)
            answer = "None"

        # 3. 验证与回退
        if not await self.remote_llm.check_answer(query, answer):
            trace.append({"step": "fallback", "reason": "verification_failed"})
            # 回退到整页推理
            whole_doc = self.cropper.pdf_to_base64(source_path)
            clean_tree_data = cctree.get_clean_structure()
            answer = await self.remote_llm.reason_whole(
                query=query, data=str(clean_tree_data), image=whole_doc
            )
        else:
            trace.append({"step": "verification", "status": "passed"})

        # 整理返回的证据文档，按页分组
        retrieved_docs = []
        if result.locations:
            pages_map = {}
            for loc in result.locations:
                p = loc.page
                if p not in pages_map:
                    pages_map[p] = []
                pages_map[p].append(loc.to_dict())

            # 这里的 content 只是展示用，由于 RetrievalResult 目前没有按页存储文本，
            # 我们简单合并所有文本作为展示，或者留空。
            all_text = "\n".join(result.text_map.values())

            for p, bboxes in pages_map.items():
                retrieved_docs.append(
                    {
                        "page": p,
                        "content": all_text[:1000],  # 限制长度
                        "bboxes": bboxes,
                    }
                )

        return {
            "answer": answer,
            "retrieved_documents": retrieved_docs,
            "retrieval_trace": trace,
        }
