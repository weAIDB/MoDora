from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Tuple

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
    evaluation_prompt,
)


def _bool_string(s: str) -> bool:
    """将字符串响应转换为布尔值。"""
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False


def _prompt_for_type(cp_type: str) -> str:
    """根据组件类型选择对应的富化提示词（Enrichment Prompt）。"""
    t = (cp_type or "").strip().lower()
    if t == "table":
        return table_enrichment_prompt
    if t == "chart":
        return chart_enrichment_prompt
    return image_enrichment_prompt


class BaseAsyncLLMClient(ABC):
    """
    异步 LLM 客户端抽象基类。
    实现通用的业务逻辑并定义 LLM 交互接口。
    """

    def __init__(self, settings: Settings | None = None):
        """初始化客户端，加载配置。"""
        self.settings = settings or Settings.load()

    @abstractmethod
    async def _call_llm(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> str:
        """
        调用底层 LLM 提供商的抽象方法。
        子类必须实现此方法以对接具体的 LLM（如 OpenAI, Anthropic 等）。
        """
        pass

    async def generate_text(self, prompt: str) -> str:
        """使用模型生成纯文本响应。"""
        return await self._call_llm(prompt) or ""

    async def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        """生成层级标题结构。"""
        prompt = level_title_prompt.format(raw_list=title_list)
        return await self._call_llm(prompt, base64_image) or ""

    async def generate_metadata(self, data: str, num: int) -> str:
        """为给定数据生成指定数量的元数据标签。"""
        prompt = metadata_generation_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def integrate_metadata(self, data: str, num: int) -> str:
        """对子节点元数据进行整合。"""
        prompt = metadata_integration_prompt.format(data=data, num=num)
        raw_response = await self._call_llm(prompt)
        response = ";".join(raw_response.split(";")[:num])
        return response

    async def parse_question(self, query: str) -> str:
        """解析用户问题，提取位置信息和问题"""
        prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", query)
        return await self._call_llm(prompt)

    async def select_children(
        self, keys: list[str], query: str, path: str, metadata_map: str
    ) -> str:
        """在树形结构中根据查询条件选择子节点。"""
        prompt = select_children_prompt.format(
            list=keys, query=query, path=path, metadata_map=metadata_map
        )
        return await self._call_llm(prompt)

    async def check_node(self, data: str, query: str) -> bool:
        """判断当前文本节点是否与查询相关。"""
        prompt = check_node_prompt1.format(data=data, query=query)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def check_node_mm(self, data: str, base64_image: str, query: str) -> bool:
        """判断当前多模态节点（文本+图片）是否与查询相关。"""
        prompt = check_node_prompt2.format(data=data, query=query)
        res = await self._call_llm(prompt, base64_image)
        return _bool_string(res)

    async def evaluate(self, query: str, reference: str, prediction: str) -> bool:
        """评估生成的答案是否与参考答案在语义上一致。"""
        prompt = evaluation_prompt.format(query=query, a=reference, b=prediction)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def check_answer(self, query: str, answer: str) -> bool:
        """检查模型生成的答案是否回答了问题。"""
        prompt = check_answer_prompt.format(query=query, answer=answer)
        res = await self._call_llm(prompt)
        return _bool_string(res)

    async def reason_retrieved(
        self, query: str, schema: str, evidence: str, images: list[str] | None = None
    ) -> str:
        """基于检索到的证据和图片进行多模态推理。"""
        prompt = image_reasoning_prompt.format(
            query=query, schema=schema, evidence=evidence
        )
        return await self._call_llm(prompt, base64_image=images)

    async def reason_whole(
        self, query: str, data: str, image: str | None = None
    ) -> str:
        """基于全局上下文进行推理。"""
        prompt = whole_reasoning_prompt.format(query=query, data=data)
        return await self._call_llm(prompt, base64_image=image)

    async def generate_annotation_async(
        self, base64_image: str, cp_type: str, settings: Settings | None = None
    ) -> Tuple[str, str, str]:
        """
        异步为图片/图表/表格生成标注（包含标题、元数据和描述内容）。
        包含重试机制以确保输出符合特定格式。
        """
        prompt = _prompt_for_type(cp_type)
        pattern = re.compile(r"\[T\](.*?)\[M\](.*?)\[C\](.*)", re.DOTALL)

        title = "Default Title"
        metadata = "Default Metadata"
        content = "Default Content"

        # 重试逻辑 (最多3次)
        for _ in range(3):
            text = await self._call_llm(prompt, base64_image) or ""
            m = pattern.search(text)
            if m:
                title = m.group(1).strip() or title
                metadata = m.group(2).strip() or metadata
                content = m.group(3).strip() or content
                break

        return title, metadata, content
