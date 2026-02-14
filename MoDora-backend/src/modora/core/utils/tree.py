from __future__ import annotations

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


def convert_tree_to_vueflow(
    cctree: dict[str, Any], root_label: str = "Document Root"
) -> list[dict[str, Any]]:
    """Convert the CCTree dictionary structure to a list of Vue Flow elements.

    Coordinates are no longer calculated on the backend; the frontend uses
    dagre for automatic layout.

    Args:
        cctree (dict[str, Any]): The CCTree dictionary.
        root_label (str): Label for the root node. Defaults to "Document Root".

    Returns:
        list[dict[str, Any]]: List of Vue Flow elements (nodes and edges).
    """
    elements = []

    def get_node_id(name: str, depth: int, index: int) -> str:
        import hashlib

        content = f"{name}-{depth}-{index}"
        return f"node-{hashlib.md5(content.encode()).hexdigest()[:8]}"

    def traverse(
        node_name: str,
        node_data: dict[str, Any],
        parent_id: str | None = None,
        depth: int = 0,
        index: int = 0,
    ):
        node_id = "root" if parent_id is None else get_node_id(node_name, depth, index)

        title = node_name
        metadata = str(node_data.get("metadata", "")).strip()
        content = str(node_data.get("data", "")).strip()

        # Backend is only responsible for assembling data; coordinates are set to 0 and handled by the frontend for layout
        elements.append(
            {
                "id": node_id,
                "type": "custom",
                "label": title,
                "data": {
                    "label": title,
                    "type": node_data.get("type", "text"),
                    "content": content[:200] + ("..." if len(content) > 200 else ""),
                    "data": content,
                    "metadata": metadata,
                    "impact": node_data.get("impact", 0),
                },
                "position": {"x": 0, "y": 0},
            }
        )

        if parent_id:
            elements.append(
                {
                    "id": f"edge-{parent_id}-{node_id}",
                    "source": parent_id,
                    "target": node_id,
                    "animated": True,
                    "style": {"stroke": "#3b82f6", "strokeWidth": 2},
                }
            )
        
        children = list(node_data.get("children", {}).items())

        for i, (child_name, child_data) in enumerate(reversed(children)):
            traverse(child_name, child_data, node_id, depth + 1, i)

    traverse(root_label, cctree)
    return elements


def reconstruct_tree_from_elements(
    elements: list[dict[str, Any]], original_tree: dict[str, Any], root_name: str
) -> dict[str, Any]:
    """Reconstruct the CCTree dictionary structure from Vue Flow elements.

    Args:
        elements (list[dict[str, Any]]): List of Vue Flow nodes and edges.
        original_tree (dict[str, Any]): The original CCTree dictionary (used to preserve data not in elements).
        root_name (str): The name of the root node.

    Returns:
        dict[str, Any]: The reconstructed CCTree dictionary.
    """
    # 1. 创建节点映射，方便通过 ID 查找
    nodes_map = {}
    edges = []
    
    # 建立原始数据的映射，以便找回 location 等信息
    original_nodes_data = {}
    def map_original(name, data):
        original_nodes_data[name] = data
        for child_name, child_data in data.get("children", {}).items():
            map_original(child_name, child_data)
    
    map_original(root_name, original_tree)

    for el in elements:
        if "source" in el and "target" in el:
            edges.append(el)
        else:
            nodes_map[el["id"]] = el

    # 2. 建立父子关系映射
    parent_to_children = {}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in parent_to_children:
            parent_to_children[source] = []
        parent_to_children[source].append(target)

    # 3. 递归构建树结构
    def build_node(node_id):
        node_el = nodes_map.get(node_id)
        if not node_el:
            return None
        
        node_name = node_el.get("label", node_el.get("data", {}).get("label", ""))
        node_data_attr = node_el.get("data", {})
        
        # 尝试从原始树中获取丢失的详细信息 (如 location)
        orig_data = original_nodes_data.get(node_name, {})
        
        reconstructed = {
            "type": node_data_attr.get("type", orig_data.get("type", "text")),
            "metadata": node_data_attr.get("metadata", orig_data.get("metadata", "")),
            "data": node_data_attr.get("data", orig_data.get("data", "")),
            "location": orig_data.get("location", []),
            "impact": node_data_attr.get("impact", orig_data.get("impact", 0)),
            "children": {}
        }

        # 递归处理子节点
        child_ids = parent_to_children.get(node_id, [])
        for child_id in reversed(child_ids):
            child_node_el = nodes_map.get(child_id)
            if child_node_el:
                child_name = child_node_el.get("label", child_node_el.get("data", {}).get("label", ""))
                child_struct = build_node(child_id)
                if child_struct:
                    reconstructed["children"][child_name] = child_struct
                    
        return reconstructed

    # 找到根节点的 ID (通常是 "root" 或者没有被作为 target 的节点)
    root_id = "root"
    if root_id not in nodes_map:
        # 如果没有固定 ID 为 root 的节点，找入度为 0 的节点
        all_targets = {e["target"] for e in edges}
        potential_roots = [nid for nid in nodes_map if nid not in all_targets]
        if potential_roots:
            root_id = potential_roots[0]

    result_tree = build_node(root_id)
    return result_tree if result_tree else original_tree
