"""MoDora Prompts Module.

This module contains all LLM Prompt templates used in core processes such as
document parsing, metadata extraction, and Retrieval-Augmented Generation (RAG).

It primarily includes the following categories of Prompts:

1. Enrichment:
    - image_enrichment_prompt: Extracts image captions, metadata, and detailed descriptions.
    - chart_enrichment_prompt: Extracts chart trends, axis information, and detailed content.
    - table_enrichment_prompt: Extracts table structure information and detailed data descriptions.

2. Hierarchy:
    - level_title_prompt: Analyzes document title hierarchy (H1-H6) based on visual information and semantics.

3. Metadata:
    - metadata_generation_prompt: Generates summary keyword phrases for text content.
    - metadata_integration_prompt: Integrates and refines multiple sets of keywords.

4. Retrieval:
    - question_parsing_prompt: Parses user questions into geographic information (page number/position) and content information.
    - select_children_prompt: Filters child nodes in the document tree that may contain evidence.
    - check_node_prompt1: Determines if a plain text node contains clues or evidence for the question.
    - check_node_prompt2: Determines if a node contains clues or evidence based on visual and textual information.
    - image_reasoning_prompt: Generates short answers based on visual and textual evidence.
    - retrieved_reasoning_prompt: Generates reasoning-based answers based on retrieved multimodal evidence.
    - whole_reasoning_prompt: Performs global reasoning based on the entire document tree structure and visual pages.
    - location_extraction_prompt: Extracts specific page numbers and 3x3 grid positions from the question.

5. Evaluation:
    - check_answer_prompt: Validates if the LLM's answer is effective (not a refusal).
    - evaluation_prompt: Evaluates if the LLM's answer is correct (based on a reference answer).
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
    rerank_prompt,
    retrieved_reasoning_prompt,
    select_children_prompt,
    whole_reasoning_prompt,
)
from .evaluation import check_answer_prompt, evaluation_prompt
from .recompose import TREE_RECOMPOSE_PROMPT

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
    "rerank_prompt",
    "retrieved_reasoning_prompt",
    "whole_reasoning_prompt",
    "location_extraction_prompt",
    "evaluation_prompt",
    "TREE_RECOMPOSE_PROMPT"
]
