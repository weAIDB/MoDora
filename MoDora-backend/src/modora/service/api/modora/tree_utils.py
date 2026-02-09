from __future__ import annotations

import json
import uuid
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
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    y_gap = 150
    x_gap = 220
    leaf_counter = 0

    def traverse(node: dict[str, Any], key_label: str, depth: int, parent_id: str | None, path: list[str]) -> str:
        nonlocal leaf_counter
        current_id = str(uuid.uuid4())
        current_path = path + [key_label]

        children_ids: list[str] = []
        for child_key, child_node in node.get("children", {}).items():
            child_id = traverse(child_node, child_key, depth + 1, current_id, current_path)
            children_ids.append(child_id)

        position_y = depth * y_gap
        if not children_ids:
            position_x = leaf_counter * x_gap
            leaf_counter += 1
        else:
            child_nodes_x = [n["position"]["x"] for n in nodes if n["id"] in children_ids]
            position_x = sum(child_nodes_x) / len(child_nodes_x) if child_nodes_x else leaf_counter * x_gap

        node_obj = {
            "id": current_id,
            "type": "custom",
            "label": key_label,
            "position": {"x": position_x, "y": position_y},
            "data": {
                "type": node.get("type", "unknown"),
                "metadata": node.get("metadata", ""),
                "id": current_id,
                "path": current_path,
                "impact": node.get("impact", 0),
            },
        }
        nodes.append(node_obj)

        if parent_id:
            edges.append(
                {
                    "id": f"e_{parent_id}_{current_id}",
                    "source": parent_id,
                    "target": current_id,
                    "animated": True,
                    "style": {"stroke": "#6366f1"},
                }
            )

        return current_id

    traverse(cctree, root_label, 0, None, [])
    return nodes + edges


def reconstruct_tree_from_elements(
    elements: list[dict[str, Any]],
    original_tree: dict[str, Any],
    root_label: str,
) -> dict[str, Any]:
    original_path_map: dict[tuple[str, ...], dict[str, Any]] = {}

    def traverse_map(node: dict[str, Any], current_path: list[str]) -> None:
        original_path_map[tuple(current_path)] = node
        for title, child in node.get("children", {}).items():
            traverse_map(child, current_path + [title])

    traverse_map(original_tree, [root_label])

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for el in elements:
        if "source" in el and "target" in el:
            edges.append(el)
        else:
            nodes[el["id"]] = el

    adj: dict[str, list[str]] = {nid: [] for nid in nodes}
    in_degree: dict[str, int] = {nid: 0 for nid in nodes}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in nodes and t in nodes:
            adj[s].append(t)
            in_degree[t] += 1

    roots = [nid for nid, d in in_degree.items() if d == 0]
    if not roots:
        raise ValueError("No root node found in the graph (cycle or empty).")

    root_id = roots[0]
    if len(roots) > 1:
        for r in roots:
            lbl = nodes[r].get("label") or nodes[r].get("data", {}).get("label")
            if lbl == root_label:
                root_id = r
                break

    def _clone_from_original(path: list[str]) -> dict[str, Any]:
        orig = original_path_map.get(tuple(path))
        if not orig:
            return {
                "type": "text",
                "metadata": "",
                "data": "",
                "location": [],
                "children": {},
                "height": 1,
                "depth": 1,
                "keyword_cnt": 0,
            }
        return {
            "type": orig.get("type", "text"),
            "metadata": orig.get("metadata", ""),
            "data": orig.get("data", ""),
            "location": orig.get("location", []),
            "children": {},
            "height": orig.get("height", 1),
            "depth": orig.get("depth", 1),
            "keyword_cnt": orig.get("keyword_cnt", 0),
        }

    def build_node(node_id: str) -> tuple[str, dict[str, Any]]:
        node = nodes[node_id]
        label = node.get("label") or node.get("data", {}).get("label") or "Untitled"
        data = node.get("data", {}) if isinstance(node.get("data"), dict) else {}
        path = data.get("path") or [root_label, label]
        if path and path[0] != root_label:
            path = [root_label] + list(path)

        new_node = _clone_from_original(path)
        if "type" in data:
            new_node["type"] = data.get("type")
        if "metadata" in data:
            new_node["metadata"] = data.get("metadata")
        if "data" in data:
            new_node["data"] = data.get("data")
        if "location" in data:
            new_node["location"] = data.get("location")

        for child_id in adj.get(node_id, []):
            child_label, child_node = build_node(child_id)
            new_node.setdefault("children", {})[child_label] = child_node

        return label, new_node

    _, root = build_node(root_id)
    if "type" not in root:
        root["type"] = "root"
    return root
