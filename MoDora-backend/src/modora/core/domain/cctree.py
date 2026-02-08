from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from modora.core.domain.component import Location, Component


@dataclass(slots=True)
class CCTreeNode:
    """
    组件树，按标题级别组织组件。
    """

    type: str
    metadata: Any | None = None
    data: str = ""
    location: list[Location] = field(default_factory=list)
    children: dict[str, "CCTreeNode"] = field(default_factory=dict)
    height: int = 1
    depth: int = 1
    keyword_cnt: int = 0

    @staticmethod
    def from_component(component: Component) -> "CCTreeNode":
        return CCTreeNode(
            type=str(component.type or ""),
            metadata=component.metadata,
            data=str(component.data or ""),
            location=list(component.location or []),
            children={},
            height=1,
            depth=1,
            keyword_cnt=0,
        )

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTreeNode":
        return CCTreeNode(
            type=obj["type"],
            metadata=obj["metadata"],
            data=obj["data"],
            location=[Location.from_dict(loc) for loc in obj["location"]],
            children={k: CCTreeNode.from_dict(v) for k, v in obj["children"].items()},
            height=obj["height"],
            depth=obj["depth"],
            keyword_cnt=obj["keyword_cnt"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
            "children": {k: v.to_dict() for k, v in self.children.items()},
            "height": self.height,
            "depth": self.depth,
            "keyword_cnt": self.keyword_cnt,
        }
    
    def has_content(self) -> bool:
        return self.data or self.location
    
    def get_metadata_map(self) -> dict[str, str]:
        return {k: v.metadata for k, v in self.children.items()}

    def get_structure(self) -> dict[str, Any]:
        """
        仅获取树的结构（递归），不包含 data/metadata/location 等详细信息。
        用于快速浏览树的形态。
        """
        children_structure = {}
        for k, v in self.children.items():
            if k != "Supplement": # Exclude Supplement by default as it's usually auxiliary
                children_structure[k] = v.get_structure()
        return children_structure

    def get_clean_structure(self) -> dict[str, Any]:
        """
        获取包含 data 的树结构，但去除 metadata/location/type 等无关信息。
        用于整树推理上下文。
        """
        res = {}
        if self.data:
            res["data"] = self.data
            
        for k, v in self.children.items():
            if k != "Supplement":
                res[k] = v.get_clean_structure()
        
        return res


@dataclass(slots=True)
class CCTree:
    """
    组件树，按标题级别组织组件。
    """

    root: CCTreeNode

    def to_dict(self) -> dict[str, Any]:
        return self.root.to_dict()

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTree":
        return CCTree(root=CCTreeNode.from_dict(obj))

    def save_json(self, path: str) -> None:
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "CCTree":
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        return CCTree.from_dict(obj)

    def get_structure(self) -> dict[str, Any]:
        """Delegate to root node."""
        return self.root.get_structure()

    def get_clean_structure(self) -> dict[str, Any]:
        """Delegate to root node."""
        return self.root.get_clean_structure()


@dataclass(slots=True)
class RetrievalResult:
    """
    检索结果集合。
    直接提供业务所需的两种数据格式：
    1. text_map: 路径到文本内容的映射，用于 LLM 推理。
    2. locations: 所有命中位置的扁平列表，用于截图。
    """
    text_map: Dict[str, str] = field(default_factory=dict)
    locations: List[Location] = field(default_factory=list)

    def update(self, other: "RetrievalResult") -> None:
        """合并另一个检索结果。"""
        self.text_map.update(other.text_map)
        self.locations.extend(other.locations)

