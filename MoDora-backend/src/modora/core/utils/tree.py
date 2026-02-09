from __future__ import annotations

import json
from typing import Any


class TreeNode:
    def __init__(
        self,
        title: str,
        typ: str | None = None,
        metadata: Any | None = None,
        data: Any | None = None,
        location: Any | None = None,
        children: list["TreeNode"] | None = None,
        path: list[str] | None = None,
        impact: int = 0,
    ):
        self.title = title
        self.type = typ
        self.metadata = metadata
        self.data = data
        self.location = location
        self.children = [] if children is None else children
        self.path = [] if path is None else path
        self.impact = impact

    def insert_child(self, child_node: "TreeNode") -> None:
        child_node.path = self.path + [child_node.title]
        self.children.append(child_node)

    def delete_child(self, child_node: "TreeNode") -> None:
        if child_node in self.children:
            self.children.remove(child_node)

    def find_child(self, title: str) -> "TreeNode" | None:
        for node in self.children:
            if node.title == title:
                return node
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "metadata": self.metadata,
            "data": self.data,
            "location": self.location,
            "impact": self.impact,
            "children": {child.title: child.to_dict() for child in self.children},
        }


def dict_to_tree(
    dict_node: dict[str, Any], root_title: str = "ROOT", path: list[str] | None = None
) -> TreeNode:
    root = TreeNode(
        title=root_title,
        typ=dict_node.get("type"),
        metadata=dict_node.get("metadata"),
        data=dict_node.get("data"),
        location=dict_node.get("location"),
        path=(path + [root_title]) if path else [root_title],
        impact=dict_node.get("impact", 0),
    )

    def add_subtree(node_dict: dict[str, Any], root_node: TreeNode) -> None:
        for sub_title, dict_child in node_dict.get("children", {}).items():
            child_node = TreeNode(
                title=sub_title,
                typ=dict_child.get("type"),
                metadata=dict_child.get("metadata"),
                data=dict_child.get("data"),
                location=dict_child.get("location"),
                impact=dict_child.get("impact", 0),
            )
            root_node.insert_child(child_node)
            add_subtree(dict_child, child_node)

    add_subtree(dict_node, root)
    return root


def validate_tree_structure(tree: dict[str, Any]) -> None:
    if not isinstance(tree, dict):
        raise ValueError("Node must be a dictionary.")
    if "type" not in tree:
        raise ValueError("Node must have a 'type' field.")
    if "children" not in tree:
        raise ValueError("Node must have a 'children' field.")
    if not isinstance(tree["children"], dict):
        raise ValueError("'children' field must be a dictionary.")

    for key, child in tree["children"].items():
        if not key or not isinstance(key, str):
            raise ValueError("Child key must be a non-empty string.")
        validate_tree_structure(child)


def convert_tree_to_vueflow(cctree: dict[str, Any], root_label: str = "Document Root") -> list[dict[str, Any]]:
    elements = []

    def traverse(node_name: str, node_data: dict[str, Any], parent_id: str | None = None):
        node_id = f"node-{node_name}-{node_data.get('type', 'none')}"
        if parent_id is None:
            node_id = "root"

        elements.append({
            "id": node_id,
            "type": "custom",
            "data": {
                "label": node_name,
                "type": node_data.get("type", "text"),
                "content": node_data.get("data", "")[:100] + ("..." if len(str(node_data.get("data", ""))) > 100 else ""),
            },
            "position": {"x": 0, "y": 0},
        })

        if parent_id:
            elements.append({
                "id": f"edge-{parent_id}-{node_id}",
                "source": parent_id,
                "target": node_id,
            })

        for child_name, child_data in node_data.get("children", {}).items():
            traverse(child_name, child_data, node_id)

    traverse(root_label, cctree)
    return elements


def reconstruct_tree_from_elements(elements: list[dict[str, Any]], original_tree: dict[str, Any], root_name: str) -> dict[str, Any]:
    # This is a complex mapping back from VueFlow elements to the CCTree dict.
    # For now, we assume simple mapping or throw error if not supported.
    return original_tree
