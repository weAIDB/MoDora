from __future__ import annotations

import re
from typing import Any
from abc import ABC, abstractmethod
from typing import Tuple

import httpx

from modora.core.settings import Settings
from modora.core.prompts import (
    chart_enrichment_prompt,
    image_enrichment_prompt,
    table_enrichment_prompt,
    level_title_prompt,
    metadata_generation_prompt,
    metadata_integration_prompt,
    question_parsing_prompt,
    select_children_prompt,
    check_node_prompt1,
    check_node_prompt2,
    check_answer_prompt,
    whole_reasoning_prompt,
    image_reasoning_prompt,
    rerank_prompt,
    evaluation_prompt,
)


def _bool_string(s: str) -> bool:
    """Convert string response to boolean value."""
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False


def _parse_score(s: str) -> float:
    if not s:
        return 0.0
    nums = re.findall(r"-?\d+(?:\.\d+)?", s)
    if not nums:
        return 0.0
    try:
        score = float(nums[0])
    except Exception:
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _prompt_for_type(cp_type: str) -> str:
    """Select the corresponding enrichment prompt based on the component type."""
    t = (cp_type or "").strip().lower()
    if t == "table":
        return table_enrichment_prompt
    if t == "chart":
        return chart_enrichment_prompt
    return image_enrichment_prompt


def _normalize_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    ep = endpoint.strip("/")
    if not ep:
        return base
    if base.endswith(f"/{ep}"):
        return base
    return f"{base}/{ep}"


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key
    return headers


async def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, json=payload, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        return response.json()


class BaseAsyncLLMClient(ABC):
    """Abstract base class for asynchronous LLM clients.

    Implements common business logic and defines LLM interaction interfaces.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the client and load the configuration."""
        self.settings = settings or Settings.load()

    @abstractmethod
    async def _call_llm(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> str:
        """Abstract method to call the underlying LLM provider.

        Subclasses must implement this method to interface with specific LLMs
        (e.g., OpenAI, Anthropic, etc.).
        """
        pass

    async def generate_text(self, prompt: str) -> str:
        """Generate a plain text response using the model."""
        return await self._call_llm(prompt) or ""

    async def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        """Generate a hierarchical title structure."""
        prompt = level_title_prompt.format(raw_list=title_list)
        return await self._call_llm(prompt, base64_image) or ""

    async def generate_metadata(self, data: str, num: int) -> str:
        """Generate a specified number of metadata tags for the given data."""
        prompt = metadata_generation_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def integrate_metadata(self, data: str, num: int) -> str:
        """Integrate metadata from child nodes."""
        prompt = metadata_integration_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def parse_question(self, query: str) -> str:
        """Parse the user's question to extract location information and the question."""
        prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", query)
        return await self._call_llm(prompt)

    async def select_children(
        self, keys: list[str], query: str, path: str, metadata_map: str
    ) -> str:
        """Select child nodes in a tree structure based on query criteria."""
        prompt = select_children_prompt.format(
            list=keys, query=query, path=path, metadata_map=metadata_map
        )
        return await self._call_llm(prompt)

    async def check_node(self, data: str, query: str) -> bool:
        """Determine if the current text node is relevant to the query."""
        prompt = check_node_prompt1.format(data=data, query=query)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def check_node_mm(self, data: str, query: str, base64_image: str) -> bool:
        """Determine if the current multimodal node (text + image) is relevant to the query."""
        prompt = check_node_prompt2.format(data=data, query=query)
        res = await self._call_llm(prompt, base64_image)
        return _bool_string(res)

    async def rerank_score(self, query: str, passage: str) -> float:
        prompt = rerank_prompt.format(query=query, passage=passage)
        res = await self._call_llm(prompt)
        return _parse_score(res or "")

    async def evaluate(self, query: str, reference: str, prediction: str) -> bool:
        """Evaluate whether the generated answer is semantically consistent with the reference answer."""
        prompt = evaluation_prompt.format(query=query, a=reference, b=prediction)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def check_answer(self, query: str, answer: str) -> bool:
        """Check if the model-generated answer addresses the question."""
        prompt = check_answer_prompt.format(query=query, answer=answer)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def reason_retrieved(
        self, query: str, schema: str, evidence: str, images: list[str] | None = None
    ) -> str:
        """Perform multimodal reasoning based on the retrieved evidence and images."""
        prompt = image_reasoning_prompt.format(
            query=query, schema=schema, evidence=evidence
        )
        return await self._call_llm(prompt, base64_image=images)

    async def reason_whole(
        self, query: str, data: str, image: str | None = None
    ) -> str:
        """Perform reasoning based on global context."""
        prompt = whole_reasoning_prompt.format(query=query, data=data)
        return await self._call_llm(prompt, base64_image=image)

    async def generate_annotation_async(
        self, base64_image: str, cp_type: str, settings: Settings | None = None
    ) -> Tuple[str, str, str]:
        """Asynchronously generate annotations (including title, metadata, and description)
        for images/charts/tables.

        Includes a retry mechanism to ensure the output adheres to a specific format.
        """
        prompt = _prompt_for_type(cp_type)
        pattern = re.compile(r"\[T\](.*?)\[M\](.*?)\[C\](.*)", re.DOTALL)

        title = "Default Title"
        metadata = "Default Metadata"
        content = "Default Content"

        # Retry logic (up to 3 times)
        for _ in range(3):
            text = await self._call_llm(prompt, base64_image) or ""
            m = pattern.search(text)
            if m:
                title = m.group(1).strip() or title
                metadata = m.group(2).strip() or metadata
                content = m.group(3).strip() or content
                break

        return title, metadata, content
