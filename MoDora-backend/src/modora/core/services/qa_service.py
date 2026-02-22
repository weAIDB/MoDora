import ast
import logging
from typing import Tuple, List

from modora.core.settings import Settings
from modora.core.domain import CCTree, RetrievalResult
from modora.core.infra.llm import AsyncLLMFactory
from modora.core.infra.pdf import PDFCropper
from modora.core.prompts import location_extraction_prompt
from modora.core.services.retrieve import (
    LocationRetriever,
    SemanticRetriever,
    VectorRetriever,
)

logger = logging.getLogger(__name__)


class QAService:
    """QA service class, responsible for coordinating retrieval, reasoning, and verification processes."""

    def __init__(
        self,
        settings: Settings | None = None,
        mode: str | None = None,
        *,
        qa_mode: str | None = None,
        retriever_mode: str | None = None,
        retriever_settings: Settings | None = None,
    ):
        self.settings = settings or Settings.load()
        self.retriever_settings = retriever_settings or self.settings

        # Backward compatibility: when mode is not split, it applies to both QA and Retriever.
        qa_mode = qa_mode or mode
        retriever_mode = retriever_mode or mode

        self.remote_llm = AsyncLLMFactory.create(
            self.settings, mode=qa_mode or "remote"
        )
        self.cropper = PDFCropper()
        self.semantic_retriever = SemanticRetriever(
            self.retriever_settings, mode=retriever_mode or "local"
        )
        self.vector_retriever = VectorRetriever(
            self.retriever_settings, mode=retriever_mode or "local"
        )
        self.location_retriever = LocationRetriever()

    async def extract_location(self, query: str) -> Tuple[List[int], List[float]]:
        """Extracts location information (page numbers and coordinates) from the query string.

        Args:
            query: The search query string.

        Returns:
            A tuple containing a list of page numbers and a list of coordinate floats.
        """
        prompt = location_extraction_prompt.format(query=query)
        response = await self.remote_llm.generate_text(prompt)
        try:
            # Expected format: "Page: [<page1>, <page2>]; Position: [<row>, <column>]"
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
        self,
        result: RetrievalResult,
        file_names: list[str] | None = None,
        retriever_by_key: (
            dict[tuple[str | None, str | None, int], set[str]] | None
        ) = None,
    ) -> list[dict]:
        """Organizes retrieved evidence documents.

        Groups bboxes from the same page of the same file into a list and associates them with corresponding text content.
        """

        retriever_by_key = retriever_by_key or {}
        locations_by_path = getattr(result, "locations_by_path", {}) or {}
        if locations_by_path:
            grouped_data: dict[tuple[str, str | None, int], dict] = {}
            for path, locs in locations_by_path.items():
                content = result.text_map.get(path, "")
                for loc in locs:
                    fn = loc.file_name
                    if not fn and file_names:
                        fn = file_names[0]
                    key = (path, fn, loc.page)
                    if key not in grouped_data:
                        grouped_data[key] = {
                            "file_name": fn,
                            "page": loc.page,
                            "content": content,
                            "bboxes": [],
                            "retrievers": sorted(
                                list(retriever_by_key.get(key, set()))
                            ),
                        }
                    if loc.bbox not in grouped_data[key]["bboxes"]:
                        grouped_data[key]["bboxes"].append(loc.bbox)
            return list(grouped_data.values())

        grouped_data: dict[tuple[str | None, str | None, int], dict] = {}
        for loc in result.locations:
            fn = loc.file_name
            if not fn and file_names:
                fn = file_names[0]
            key = (None, fn, loc.page)
            if key not in grouped_data:
                content = ""
                for path, text in result.text_map.items():
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
                    "retrievers": sorted(list(retriever_by_key.get(key, set()))),
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
        """Executes the complete QA workflow: location extraction -> retrieval -> reasoning -> verification/fallback.

        Args:
            tree (CCTree): The concept tree.
            query (str): The user query.
            source_path (str | dict[str, str]): Path to the source document(s).

        Returns:
            dict: The QA response and trace information.
        """
        page_list, position_vector = await self.extract_location(query)

        result = RetrievalResult()

        # 1. Retrieval
        if -1 in page_list and position_vector == [-1.0, -1.0]:
            semantic_result = await self.semantic_retriever.retrieve(
                tree, query, source_path
            )
            vector_result = await self.vector_retriever.retrieve(
                tree, query, source_path
            )
            result.update(semantic_result)
            result.update(vector_result)
        else:
            # Location retrieval currently only supports single documents; can be extended later
            actual_source = (
                list(source_path.values())[0]
                if isinstance(source_path, dict)
                else source_path
            )
            result = self.location_retriever.retrieve(
                tree, page_list, position_vector, actual_source
            )

        # 2. Process results and reason
        schema = tree.get_structure()
        answer = "None"
        trace = [
            {
                "step": "extract_location",
                "page_list": page_list,
                "position_vector": position_vector,
            },
            {
                "step": "retrieve",
                "locations_count": len(result.locations),
                "semantic_locations_count": (
                    len(semantic_result.locations)
                    if -1 in page_list and position_vector == [-1.0, -1.0]
                    else 0
                ),
                "vector_locations_count": (
                    len(vector_result.locations)
                    if -1 in page_list and position_vector == [-1.0, -1.0]
                    else 0
                ),
            },
        ]

        file_names = list(source_path.keys()) if isinstance(source_path, dict) else None
        retriever_by_key: dict[tuple[str | None, str | None, int], set[str]] = {}

        def add_retriever_map(
            retrieval_result: RetrievalResult, retriever: str
        ) -> None:
            locations_by_path = getattr(retrieval_result, "locations_by_path", {}) or {}
            if locations_by_path:
                for path, locs in locations_by_path.items():
                    for loc in locs:
                        fn = loc.file_name
                        if not fn and file_names:
                            fn = file_names[0]
                        key = (path, fn, loc.page)
                        retriever_by_key.setdefault(key, set()).add(retriever)
            else:
                for loc in retrieval_result.locations:
                    fn = loc.file_name
                    if not fn and file_names:
                        fn = file_names[0]
                    key = (None, fn, loc.page)
                    retriever_by_key.setdefault(key, set()).add(retriever)

        try:
            if result.locations or result.text_map:
                # Crop images based on precise locations
                images = self.cropper.crop_image(
                    source_path, result.locations, file_names=file_names
                )

                logger.info(
                    f"Reasoning with {len(result.text_map)} text segments and {len(images)} images",
                    extra={
                        "text_keys": list(result.text_map.keys()),
                        "locations_count": len(result.locations),
                    },
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

        # 3. Verification and fallback
        if not await self.remote_llm.check_answer(query, answer):
            trace.append({"step": "fallback", "reason": "verification_failed"})
            # Fallback to whole-page reasoning (multi-document mode does not support whole-page fallback yet, or only for the first document)
            if isinstance(source_path, str):
                whole_doc = self.cropper.pdf_to_base64(source_path)
                clean_tree_data = tree.get_clean_structure()
                answer = await self.remote_llm.reason_whole(
                    query=query, data=str(clean_tree_data), image=whole_doc
                )
            else:
                logger.warning(
                    "Multi-doc mode does not support whole-page fallback yet"
                )
        else:
            trace.append({"step": "verification", "status": "passed"})

        if -1 in page_list and position_vector == [-1.0, -1.0]:
            add_retriever_map(semantic_result, "semantic")
            add_retriever_map(vector_result, "vector")
        else:
            add_retriever_map(result, "location")

        retrieved_docs = self._format_retrieved_docs(
            result, file_names=file_names, retriever_by_key=retriever_by_key
        )

        # Update the impact values of tree nodes
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
