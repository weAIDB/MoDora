"""
MoDora Prompts 模块

该模块包含了文档解析、元数据提取、检索增强生成 (RAG) 等核心流程中使用的所有 LLM Prompt 模板。

主要包含以下几类 Prompt：

1. Enrichment (内容增强):
    - image_enrichment_prompt: 提取图片的标题、元数据及详细描述。
    - chart_enrichment_prompt: 提取图表的趋势、坐标轴信息及详细内容。
    - table_enrichment_prompt: 提取表格的结构信息及详细数据描述。

2. Hierarchy (层级分析):
    - level_title_prompt: 根据视觉信息和语义分析文档标题的层级（H1-H6）。

3. Metadata (元数据提取):
    - metadata_generation_prompt: 为文本内容生成总结性的关键词短语。
    - metadata_integration_prompt: 对多组关键词进行整合与精炼。

4. Retrieval (检索与推理):
    - question_parsing_prompt: 将用户问题解析为地理位置信息（页码/方位）和内容信息。
    - select_children_prompt: 在文档树中筛选可能包含证据的子节点。
    - check_node_prompt1: 判断纯文本节点是否包含问题的线索或证据。
    - check_node_prompt2: 结合视觉和文本判断节点是否包含问题的线索或证据。
    - image_reasoning_prompt: 基于视觉证据和文本证据生成简短回答。
    - retrieved_reasoning_prompt: 基于检索到的多模态证据进行推理回答。
    - whole_reasoning_prompt: 基于整个文档树结构和视觉页面进行全局推理。
    - location_extraction_prompt: 从问题中提取具体的页码和页面九宫格位置。

5. Evaluation (评估):
    - check_answer_prompt: 验证 LLM 的回答是否有效（非拒绝回答）。
    - evaluation_prompt: 评估 LLM 回答是否正确（基于参考答案）。
"""

from .enrichment import (
    chart_enrichment_prompt,
    image_enrichment_prompt,
    table_enrichment_prompt,
)
from .hierarchy import level_title_prompt
from .metadata import (
    metadata_generation_prompt,
    metadata_integration_prompt,
)
from .retrieval import (
    check_node_prompt1,
    check_node_prompt2,
    image_reasoning_prompt,
    location_extraction_prompt,
    question_parsing_prompt,
    retrieved_reasoning_prompt,
    select_children_prompt,
    whole_reasoning_prompt,
)
from .evaluation import check_answer_prompt, evaluation_prompt

__all__ = [
    "image_enrichment_prompt",
    "chart_enrichment_prompt",
    "table_enrichment_prompt",
    "level_title_prompt",
    "metadata_generation_prompt",
    "metadata_integration_prompt",
    "question_parsing_prompt",
    "select_children_prompt",
    "check_node_prompt1",
    "check_node_prompt2",
    "check_answer_prompt",
    "image_reasoning_prompt",
    "retrieved_reasoning_prompt",
    "whole_reasoning_prompt",
    "location_extraction_prompt",
    "evaluation_prompt",
]
