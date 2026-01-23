from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    
    @staticmethod
    def from_component(component: Component) -> "CCTreeNode":
        return CCTreeNode(
            type=str(component.type or ""),
            metadata=component.metadata,
            data=str(component.data or ""),
            location=list(component.location or []),
            children={},
        )

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTreeNode":
        return CCTreeNode(
            type=obj["type"],
            metadata=obj["metadata"],
            data=obj["data"],
            location=[Location.from_dict(loc) for loc in obj["location"]],
            children={k: CCTreeNode.from_dict(v) for k, v in obj["children"].items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
            "children": {k: v.to_dict() for k, v in self.children.items()},
        }
    

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
            encoding="utf-8"
        )

    @staticmethod
    def load_json(path: str) -> "CCTree":
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        return CCTree.from_dict(obj)
