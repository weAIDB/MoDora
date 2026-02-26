from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    file_name: str | None = None
    file_names: list[str] | None = None
    query: str
    settings: dict[str, Any] | None = None


class RetrievalItem(BaseModel):
    page: int
    content: str
    bboxes: list[Any]
    score: float | None = 0.0
    file_name: str | None = None


class ChatResponse(BaseModel):
    answer: str
    reasoning_log: str | None = ""
    retrieved_documents: list[RetrievalItem] = []
    node_impacts: dict[str, int] = {}


class TreeRequest(BaseModel):
    file_name: str


class TreeResponse(BaseModel):
    elements: list


class TreeUpdateRequest(BaseModel):
    file_name: str
    elements: list


class TreeRecomposeRequest(BaseModel):
    file_name: str
    rule: str = "balanced"
    user_query: str | None = None
    settings: dict[str, Any] | None = None


class NodeUpdateRequest(BaseModel):
    file_name: str
    action: str
    target_path: list[str]
    new_data: dict[str, Any] | None = None


class DocStatsResponse(BaseModel):
    pages: int
    counts: dict[str, int]
    variance: float
    nodes: int
    leaves: int
    depth: int
    tags: list[str] = []
    semantic_tags: list[str] = []


class SessionStatsRequest(BaseModel):
    file_names: list[str]


class SessionStatsResponse(BaseModel):
    total_files: int
    avg_pages: float
    avg_nodes: float
    avg_depth: float
    total_counts: dict[str, int]
    avg_variance: float


class UpdateTagsRequest(BaseModel):
    file_name: str
    tags: list[str]
