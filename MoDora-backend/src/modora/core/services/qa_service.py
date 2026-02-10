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

    def __init__(self, settings: Settings | None = None, mode: str | None = None):
        self.settings = settings or Settings()
        # 如果指定了 mode，则所有 LLM 客户端都使用该 mode
        # 否则，local_llm 强制 local，remote_llm 强制 remote
        self.local_llm = AsyncLLMFactory.create(self.settings, mode=mode or "local")
        self.remote_llm = AsyncLLMFactory.create(self.settings, mode=mode or "remote")
        self.cropper = PDFCropper()
        self.semantic_retriever = SemanticRetriever(self.settings, mode=mode)
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

    def _format_retrieved_docs(
        self, result: RetrievalResult, file_names: list[str] | None = None
    ) -> list[dict]:
        """
        整理检索到的证据文档。
        将同一个文件同一页的 bbox 合并到一个列表中，并关联对应的文本内容。
        """
        if not result.locations:
            return []

        # (file_name, page) -> {bboxes, content}
        grouped_data: dict[tuple[str | None, int], dict] = {}

        for loc in result.locations:
            fn = loc.file_name
            if not fn and file_names:
                fn = file_names[0]

            key = (fn, loc.page)
            if key not in grouped_data:
                # 查找该节点对应的文本
                content = ""
                for path, text in result.text_map.items():
                    # 如果 path 中包含文件名或 path 本身就是我们要找的内容
                    if fn and fn in path:
                        content = text
                        break
                    elif not fn:
                        content = text
                        break

                grouped_data[key] = {
                    "file_name": fn,
                    "page": loc.page,
                    "content": content,
                    "bboxes": [],
                }

            if loc.bbox not in grouped_data[key]["bboxes"]:
                grouped_data[key]["bboxes"].append(loc.bbox)

        return list(grouped_data.values())

    async def qa(
        self,
        tree: CCTree,
        query: str,
        source_path: str | dict[str, str],
    ) -> dict:
        """
        执行完整的 QA 流程：提取位置 -> 检索 -> 推理 -> 验证/回退。
        """
        page_list, position_vector = await self.extract_location(query)

        result = RetrievalResult()

        # 1. 检索
        if -1 in page_list and position_vector == [-1.0, -1.0]:
            result = await self.semantic_retriever.retrieve(tree, query, source_path)
        else:
            # 位置检索目前仅支持单文档，后续可扩展
            actual_source = (
                list(source_path.values())[0]
                if isinstance(source_path, dict)
                else source_path
            )
            result = self.location_retriever.retrieve(
                tree, page_list, position_vector, actual_source
            )

        # 2. 处理结果并推理
        schema = tree.get_structure()
        answer = "None"
        trace = [
            {
                "step": "extract_location",
                "page_list": page_list,
                "position_vector": position_vector,
            },
            {"step": "retrieve", "locations_count": len(result.locations)},
        ]

        file_names = list(source_path.keys()) if isinstance(source_path, dict) else None

        try:
            if result.locations or result.text_map:
                # 根据精确位置裁剪图像
                images = self.cropper.crop_image(
                    source_path, result.locations, file_names=file_names
                )

                logger.info(
                    f"Reasoning with {len(result.text_map)} text segments and {len(images)} images",
                    extra={
                        "text_keys": list(result.text_map.keys()),
                        "locations_count": len(result.locations)
                    }
                )

                answer = await self.remote_llm.reason_retrieved(
                    query=query,
                    evidence=str(result.text_map),
                    images=images,
                    schema=str(schema),
                )
            else:
                logger.warning("No retrieval results found, skipping normal reasoning")
                answer = "None"

        except Exception as e:
            logger.error(f"Error in reasoning: {e}", exc_info=True)
            answer = "None"

        # 3. 验证与回退
        if not await self.remote_llm.check_answer(query, answer):
            trace.append({"step": "fallback", "reason": "verification_failed"})
            # 回退到整页推理 (多文档模式下暂不支持全页回退，或者只对第一文档做)
            if isinstance(source_path, str):
                whole_doc = self.cropper.pdf_to_base64(source_path)
                clean_tree_data = tree.get_clean_structure()
                answer = await self.remote_llm.reason_whole(
                    query=query, data=str(clean_tree_data), image=whole_doc
                )
            else:
                logger.warning("Multi-doc mode does not support whole-page fallback yet")
        else:
            trace.append({"step": "verification", "status": "passed"})

        # 整理返回的证据文档
        retrieved_docs = self._format_retrieved_docs(result, file_names=file_names)

        # 更新树节点的 impact 值
        all_impact_updates = {}
        for path in result.text_map.keys():
            updates = tree.update_impact(path)
            all_impact_updates.update(updates)

        return {
            "answer": answer,
            "retrieved_documents": retrieved_docs,
            "node_impacts": all_impact_updates,
            "retrieval_trace": trace,
        }
