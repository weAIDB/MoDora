from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from modora.core.domain.component import Location, Component


@dataclass(slots=True)
class CCTreeNode:
    """
    组件树节点 (Component-Correlation Tree Node)。
    按标题级别组织文档组件，支持递归结构。

    Attributes:
        type: 组件类型 (如 'text', 'image', 'table', 'header' 等)。
        metadata: 元数据，存储与组件相关的额外信息 (如表格的行列信息)。
        data: 组件的具体内容 (文本内容或 OCR 结果)。
        location: 组件在 PDF 页面上的位置列表 (可能跨页)。
        children: 子节点映射，Key 通常为子标题或序号。
        height: 节点高度 (从叶子节点到当前节点的路径长度)。
        depth: 节点深度 (从根节点到当前节点的路径长度)。
        keyword_cnt: 关键词命中计数 (用于检索评分)。
    """

    type: str
    metadata: Any | None = None
    data: str = ""
    location: list[Location] = field(default_factory=list)
    children: dict[str, "CCTreeNode"] = field(default_factory=dict)
    height: int = 1
    depth: int = 1
    keyword_cnt: int = 0
    impact: int = 0

    @staticmethod
    def from_component(component: Component) -> "CCTreeNode":
        """从基础组件 Component 转换为树节点。"""
        return CCTreeNode(
            type=str(component.type or ""),
            metadata=component.metadata,
            data=str(component.data or ""),
            location=list(component.location or []),
            children={},
            height=1,
            depth=1,
            keyword_cnt=0,
            impact=0,
        )

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTreeNode":
        """从字典反序列化为树节点。"""
        return CCTreeNode(
            type=obj["type"],
            metadata=obj["metadata"],
            data=obj["data"],
            location=[Location.from_dict(loc) for loc in obj["location"]],
            children={k: CCTreeNode.from_dict(v) for k, v in obj["children"].items()},
            height=obj["height"],
            depth=obj["depth"],
            keyword_cnt=obj["keyword_cnt"],
            impact=obj.get("impact", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        """将树节点序列化为字典。"""
        return {
            "type": self.type,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
            "children": {k: v.to_dict() for k, v in self.children.items()},
            "height": self.height,
            "depth": self.depth,
            "keyword_cnt": self.keyword_cnt,
            "impact": self.impact,
        }

    def has_content(self) -> bool:
        """检查节点是否包含有效内容 (数据或位置信息)。"""
        return bool(self.data or self.location)

    def get_metadata_map(self) -> dict[str, Any]:
        """获取所有子节点的元数据映射。"""
        return {k: v.metadata for k, v in self.children.items()}

    def get_structure(self) -> dict[str, Any]:
        """
        获取树的骨架结构 (递归)。
        不包含 data/metadata/location 等详细内容，仅保留层级关系。
        用于正常问答
        """
        children_structure = {}
        for k, v in self.children.items():
            if k != "Supplement":  # 默认排除辅助性的 Supplement 节点
                children_structure[k] = v.get_structure()
        return children_structure

    def get_clean_structure(self) -> dict[str, Any]:
        """
        获取包含 data 的精简树结构。
        去除 metadata/location/type 等非文本信息。
        用于兜底问答
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
    组件树 (Component-Correlation Tree)。
    管理整份文档的层级结构。
    """

    root: CCTreeNode

    def to_dict(self) -> dict[str, Any]:
        """序列化整棵树。"""
        return self.root.to_dict()

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTree":
        """从字典反序列化整棵树。"""
        return CCTree(root=CCTreeNode.from_dict(obj))

    @staticmethod
    def merge_multi_trees(trees: dict[str, CCTree]) -> "CCTree":
        """
        将多个文档的 CCTree 合并为一个多文档树。
        原来的文档树根节点将以其文件名作为 key，挂载到一个新的 'multi_doc_root' 节点下。

        Args:
            trees: 文件名到 CCTree 的映射。

        Returns:
            合并后的 CCTree。
        """
        multi_root = CCTreeNode(
            type="multi_doc_root",
            metadata="Combined tree for multi-document session",
            data="",
            location=[],
            children={},
            height=0,
            depth=0,
            keyword_cnt=0,
        )

        max_height = 0
        for file_name, tree in trees.items():
            # 遍历树，为所有 Location 注入 file_name
            CCTree._inject_file_name(tree.root, file_name)

            # 将文档树作为子节点挂载，以文件名作为标题
            multi_root.children[file_name] = tree.root
            max_height = max(max_height, tree.root.height)

        # 更新根节点高度
        multi_root.height = max_height + 1
        return CCTree(root=multi_root)

    @staticmethod
    def _inject_file_name(node: CCTreeNode, file_name: str) -> None:
        """递归为节点及其子节点的所有 Location 注入文件名。"""
        if node.location:
            for loc in node.location:
                loc.file_name = file_name

        if node.children:
            for child in node.children.values():
                CCTree._inject_file_name(child, file_name)

    def save_json(self, path: str) -> None:
        """将树保存为 JSON 文件。"""
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "CCTree":
        """从 JSON 文件加载树。"""
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        return CCTree.from_dict(obj)

    def get_structure(self) -> dict[str, Any]:
        """获取整棵树的骨架结构。"""
        return self.root.get_structure()

    def get_clean_structure(self) -> dict[str, Any]:
        """获取整棵树的精简结构。"""
        return self.root.get_clean_structure()

    def find_node_by_path(self, path: str) -> CCTreeNode | None:
        """
        根据路径字符串查找节点。
        路径格式如: "Root--Child1--GrandChild1"
        """
        parts = path.split("--")
        if not parts:
            return None

        current = self.root
        # 兼容性处理：如果 path 只有一部分且匹配 root，直接返回
        if len(parts) == 1:
            return current

        # 尝试逐层查找
        for part in parts[1:]:
            if part in current.children:
                current = current.children[part]
            else:
                return None
        return current

    def update_impact(self, path: str) -> dict[str, int]:
        """
        更新路径上节点的热度值。
        - 路径上的中间节点: impact + 1
        - 目标叶子节点: impact + 2
        
        返回更新后的 {path: impact} 映射。
        """
        parts = path.split("--")
        if not parts:
            return {}

        impact_updates = {}
        current = self.root
        current_path = parts[0]
        
        # 根节点处理 (+1)
        current.impact += 1
        impact_updates[current_path] = current.impact

        # 逐层向下更新
        for i, part in enumerate(parts[1:]):
            if part in current.children:
                current = current.children[part]
                current_path += f"--{part}"
                
                # 判断是否是最后一个节点（目标节点）
                if i == len(parts) - 2:
                    current.impact += 2
                else:
                    current.impact += 1
                
                impact_updates[current_path] = current.impact
            else:
                break
                
        return impact_updates


@dataclass(slots=True)
class RetrievalResult:
    """
    检索结果集合。
    封装了检索过程中命中的文本和对应的位置信息。

    Attributes:
        text_map: 路径到文本内容的映射。Key 为节点路径，Value 为该节点的文本。用于 LLM 推理。
        locations: 命中的位置列表。包含所有命中节点的 Location 信息，用于截图或高亮显示。
    """

    text_map: Dict[str, str] = field(default_factory=dict)
    locations: List[Location] = field(default_factory=list)

    def update(self, other: "RetrievalResult") -> None:
        """
        合并另一个检索结果。

        Args:
            other: 待合并的 RetrievalResult 对象。
        """
        self.text_map.update(other.text_map)
        self.locations.extend(other.locations)
