from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from typing import Tuple

from modora.core.settings import Settings
from modora.core.prompts.enrichment import (
    chart_enrichment_prompt,
    image_enrichment_prompt,
    table_enrichment_prompt,
)
from modora.core.prompts.hierarchy import level_title_prompt
from modora.core.prompts.metadata import (
    metadata_generation_prompt,
    metadata_integration_prompt,
)
from modora.core.prompts.retrieval import (
    question_parsing_prompt,
    select_children_prompt,
    check_node_prompt1,
    check_node_prompt2,
    check_answer_prompt,
    retrieved_reasoning_prompt,
    whole_reasoning_prompt,
)


def _bool_string(s: str) -> bool:
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False


def _prompt_for_type(cp_type: str) -> str:
    """Select enrichment prompt based on component type."""
    t = (cp_type or "").strip().lower()
    if t == "table":
        return table_enrichment_prompt
    if t == "chart":
        return chart_enrichment_prompt
    return image_enrichment_prompt


class BaseAsyncLLMClient(ABC):
    """
    Abstract base class for Async LLM Clients.
    Implements common business logic and defines the interface for LLM interaction.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()

    @abstractmethod
    async def _call_llm(self, prompt: str, base64_image: str | None = None) -> str:
        """
        Abstract method to call the underlying LLM provider.
        Must be implemented by subclasses.
        """
        pass

    async def generate_text(self, prompt: str) -> str:
        """Generate text using the model."""
        return await self._call_llm(prompt) or ""

    async def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        prompt = level_title_prompt.format(raw_list=title_list)
        return await self._call_llm(prompt, base64_image) or ""

    async def generate_metadata(self, data: str, num: int) -> str:
        prompt = metadata_generation_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def integrate_metadata(self, data: str, num: int) -> str:
        prompt = metadata_integration_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def parse_question(self, query: str) -> str:
        prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", query)
        return await self._call_llm(prompt)

    async def select_children(
        self, keys: list[str], query: str, path: str, metadata_map: str
    ) -> str:
        prompt = select_children_prompt.format(
            list=keys, query=query, path=path, metadata_map=metadata_map
        )
        return await self._call_llm(prompt)

    async def check_node(self, data: str, query: str) -> bool:
        prompt = check_node_prompt1.format(data=data, query=query)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def check_node_mm(self, data: str, base64_image: str, query: str) -> bool:
        prompt = check_node_prompt2.format(data=data, query=query)
        res = await self._call_llm(prompt, base64_image)
        return _bool_string(res)

    async def check_answer(self, query: str, answer: str) -> bool:
        prompt = check_answer_prompt.format(query=query, answer=answer)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def reason_retrieved(self, query: str, schema: str, evidence: str) -> str:
        prompt = retrieved_reasoning_prompt.format(
            query=query, schema=schema, evidence=evidence
        )
        return await self._call_llm(prompt)

    async def reason_whole(self, query: str, data: str) -> str:
        prompt = whole_reasoning_prompt.format(query=query, data=data)
        return await self._call_llm(prompt)

    async def generate_annotation_async(
        self, base64_image: str, cp_type: str, settings: Settings | None = None
    ) -> Tuple[str, str, str]:
        """
        Asynchronously generate annotation for an image.
        """
        prompt = _prompt_for_type(cp_type)
        pattern = re.compile(r"\[T\](.*?)\[M\](.*?)\[C\](.*)", re.DOTALL)

        title = "Default Title"
        metadata = "Default Metadata"
        content = "Default Content"

        # Retry logic
        for _ in range(3):
            text = await self._call_llm(prompt, base64_image) or ""
            m = pattern.search(text)
            if m:
                title = m.group(1).strip() or title
                metadata = m.group(2).strip() or metadata
                content = m.group(3).strip() or content
                break
        
        return title, metadata, content
