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

    def to_flat_list(self) -> list[dict[str, Any]]:
        """Flatten the tree structure into a list of nodes for easier AI processing."""
        nodes = []
        nodes.append({
            "title": self.title,
            "type": self.type,
            "metadata": self.metadata,
            "content_summary": (self.data[:100] + "...") if isinstance(self.data, str) and len(self.data) > 100 else self.data
        })
        for child in self.children:
            nodes.extend(child.to_flat_list())
        return nodes

    def get_schema(self) -> dict[str, Any]:
        """Extract the tree structure's schema (a simplified version, removing redundant information)."""
        return {
            "title": self.title,
            "type": self.type,
            "children": [child.get_schema() for child in self.children]
        }

    def recompose_by_schema(self, ai_schema: dict[str, Any]) -> "TreeNode":
        """
        Reconstruct the tree structure based on the AI-generated schema and inherit node information from the current tree.
        """
        return recompose_tree_with_ai(self, ai_schema)


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
    # 1. Create node mapping for easy lookup by ID
    nodes_map = {}
    edges = []

    # Map original data to retrieve location and other details
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

    # 2. Establish parent-child relationship mapping
    parent_to_children = {}
    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in parent_to_children:
            parent_to_children[source] = []
        parent_to_children[source].append(target)

    # 3. Recursively build the tree structure
    def build_node(node_id):
        node_el = nodes_map.get(node_id)
        if not node_el:
            return None

        node_name = node_el.get("label", node_el.get("data", {}).get("label", ""))
        node_data_attr = node_el.get("data", {})

        # Try to retrieve missing details (e.g., location) from the original tree
        orig_data = original_nodes_data.get(node_name, {})

        reconstructed = {
            "type": node_data_attr.get("type", orig_data.get("type", "text")),
            "metadata": node_data_attr.get("metadata", orig_data.get("metadata", "")),
            "data": node_data_attr.get("data", orig_data.get("data", "")),
            "location": orig_data.get("location", []),
            "impact": node_data_attr.get("impact", orig_data.get("impact", 0)),
            "keyword_cnt": orig_data.get("keyword_cnt", 0),
            "children": {},
        }

        # Recursively process child nodes
        child_ids = parent_to_children.get(node_id, [])
        for child_id in reversed(child_ids):
            child_node_el = nodes_map.get(child_id)
            if child_node_el:
                child_name = child_node_el.get(
                    "label", child_node_el.get("data", {}).get("label", "")
                )
                child_struct = build_node(child_id)
                if child_struct:
                    reconstructed["children"][child_name] = child_struct

        return reconstructed

    # Find the root node ID (usually "root" or a node that is not a target)
    root_id = "root"
    if root_id not in nodes_map:
        # If no fixed "root" node ID, find the node with in-degree 0
        all_targets = {e["target"] for e in edges}
        potential_roots = [nid for nid in nodes_map if nid not in all_targets]
        if potential_roots:
            root_id = potential_roots[0]

    result_tree = build_node(root_id)
    return result_tree if result_tree else original_tree


def recompose_tree_with_ai(
    original_root: TreeNode, ai_schema: dict[str, Any]
) -> TreeNode:
    """
    Reconstruct the tree structure based on the AI-generated schema and inherit information from the original nodes.
    Example of ai_schema format:
    {
        "title": "New Root",
        "type": "chapter",
        "children": [
            { "title": "Old Node A", "type": "section", "children": [] },
            { "title": "New Category", "type": "chapter", "children": [...] }
        ]
    }
    """
    # 1. Establish mapping for original node data (based on titles)
    original_nodes_map = {}

    def map_nodes(node: TreeNode):
        # If there are duplicate titles, they will be overwritten here.
        # In actual application, more complex logic (like combining with path) might be needed.
        original_nodes_map[node.title] = node
        for child in node.children:
            map_nodes(child)

    map_nodes(original_root)

    # 2. Recursively build the new tree
    def build_from_ai(schema_node: dict[str, Any]) -> TreeNode:
        title = schema_node.get("title", "Untitled")
        typ = schema_node.get("type", "text")
        
        # Try to find the original node to inherit information
        orig_node = original_nodes_map.get(title)
        
        if orig_node:
            # Inherit original information
            new_node = TreeNode(
                title=title,
                typ=typ or orig_node.type, # Prioritize type specified by AI
                metadata=orig_node.metadata,
                data=orig_node.data,
                location=orig_node.location,
                impact=orig_node.impact,
            )
        else:
            # New node created by AI (e.g., category directory)
            new_node = TreeNode(
                title=title,
                typ=typ,
                metadata="",
                data="",
                location=[],
                impact=0
            )
            
        # Process child nodes
        for child_schema in schema_node.get("children", []):
            new_node.insert_child(build_from_ai(child_schema))
            
        return new_node

    return build_from_ai(ai_schema)


def recompose_tree_dict(
    tree_dict: dict[str, Any], root_title: str, rule: str
) -> dict[str, Any]:
    root = dict_to_tree(tree_dict, root_title=root_title)

    def sort_children(node: TreeNode, key_fn) -> None:
        node.children.sort(key=key_fn)
        for child in node.children:
            sort_children(child, key_fn)

    def collect_nodes(node: TreeNode, out: list[TreeNode]) -> None:
        for child in node.children:
            out.append(child)
            collect_nodes(child, out)

    def clone_node(node: TreeNode) -> TreeNode:
        return TreeNode(
            title=node.title,
            typ=node.type,
            metadata=node.metadata,
            data=node.data,
            location=node.location,
            impact=node.impact,
        )

    if rule == "type_first":
        sort_children(root, lambda n: ((n.type or ""), n.title))
        return root.to_dict()

    if rule == "shuffle":
        import random

        rng = random.Random()

        def shuffle_children(node: TreeNode) -> None:
            rng.shuffle(node.children)
            for child in node.children:
                shuffle_children(child)

        shuffle_children(root)
        return root.to_dict()

    if rule == "balanced":
        nodes: list[TreeNode] = []
        collect_nodes(root, nodes)
        nodes.sort(key=lambda n: ((n.type or ""), n.title))
        new_root = clone_node(root)
        queue = [new_root]
        parent_index = 0
        index = 0
        k = 3
        while index < len(nodes):
            parent = queue[parent_index]
            parent_index += 1
            for _ in range(k):
                if index >= len(nodes):
                    break
                child = clone_node(nodes[index])
                index += 1
                parent.insert_child(child)
                queue.append(child)
        return new_root.to_dict()

    return root.to_dict()
