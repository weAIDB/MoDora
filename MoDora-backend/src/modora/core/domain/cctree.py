from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from modora.core.domain.component import Location, Component


@dataclass(slots=True)
class CCTreeNode:
    """Component-Correlation Tree Node (CCTreeNode).

    Organizes document components by heading level and supports recursive structures.

    Attributes:
        type (str): Component type (e.g., 'text', 'image', 'table', 'header').
        metadata (Any | None): Metadata storing additional information related to the component (e.g., table row/column info).
        data (str): Specific content of the component (text content or OCR results).
        location (list[Location]): List of locations of the component on PDF pages (may span multiple pages).
        children (dict[str, "CCTreeNode"]): Mapping of child nodes, where the key is usually a sub-heading or sequence number.
        height (int): Node height (path length from a leaf node to the current node).
        depth (int): Node depth (path length from the root node to the current node).
        keyword_cnt (int): Keyword hit count (used for retrieval scoring).
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
        """Converts a base component into a tree node.

        Args:
            component (Component): The base component to convert.

        Returns:
            CCTreeNode: The converted tree node.
        """
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
        """Deserializes a dictionary into a tree node.

        Args:
            obj (dict[str, Any]): The dictionary to deserialize.

        Returns:
            CCTreeNode: The deserialized tree node.
        """
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
        """Serializes the tree node into a dictionary.

        Returns:
            dict[str, Any]: The serialized dictionary.
        """
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
        """Checks if the node contains valid content (data or location information).

        Returns:
            bool: True if the node has data or location information, False otherwise.
        """
        return bool(self.data or self.location)

    def get_metadata_map(self) -> dict[str, Any]:
        """Gets a mapping of metadata for all child nodes.

        Returns:
            dict[str, Any]: A dictionary mapping child keys to their metadata.
        """
        return {k: v.metadata for k, v in self.children.items()}

    def get_structure(self) -> dict[str, Any]:
        """Gets the skeletal structure of the tree recursively.

        Excludes detailed content such as data, metadata, and location,
        retaining only hierarchical relationships. Used for standard Q&A.

        Returns:
            dict[str, Any]: A recursive dictionary representing the tree structure.
        """
        children_structure = {}
        for k, v in self.children.items():
            if k != "Supplement":  # Exclude auxiliary Supplement nodes by default.
                children_structure[k] = v.get_structure()
        return children_structure

    def get_clean_structure(self) -> dict[str, Any]:
        """Gets a simplified tree structure containing data.

        Removes non-text information such as metadata, location, and type.
        Used for fallback Q&A.

        Returns:
            dict[str, Any]: A simplified recursive dictionary of the tree.
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
    """Component-Correlation Tree (CCTree).

    Manages the hierarchical structure of an entire document.
    """

    root: CCTreeNode

    def to_dict(self) -> dict[str, Any]:
        """Serializes the entire tree.

        Returns:
            dict[str, Any]: The serialized dictionary representation of the tree.
        """
        return self.root.to_dict()

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "CCTree":
        """Deserializes the entire tree from a dictionary.

        Args:
            obj (dict[str, Any]): The dictionary to deserialize.

        Returns:
            CCTree: The deserialized CCTree instance.
        """
        return CCTree(root=CCTreeNode.from_dict(obj))

    @staticmethod
    def merge_multi_trees(trees: dict[str, CCTree]) -> "CCTree":
        """Merges CCTrees from multiple documents into a single multi-document tree.

        The original document tree root nodes will be mounted under a new 'multi_doc_root'
        node using their file names as keys.

        Args:
            trees (dict[str, CCTree]): A mapping from file names to CCTrees.

        Returns:
            CCTree: The merged CCTree.
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
            # Traverse the tree and inject the file_name into all Locations.
            CCTree._inject_file_name(tree.root, file_name)

            # Mount the document tree as a child node, using the file name as the heading.
            multi_root.children[file_name] = tree.root
            max_height = max(max_height, tree.root.height)

        # Update the root node height.
        multi_root.height = max_height + 1
        return CCTree(root=multi_root)

    @staticmethod
    def _inject_file_name(node: CCTreeNode, file_name: str) -> None:
        """Recursively injects the file name into all Locations of the node and its children.

        Args:
            node (CCTreeNode): The node to process.
            file_name (str): The file name to inject.
        """
        if node.location:
            for loc in node.location:
                loc.file_name = file_name

        if node.children:
            for child in node.children.values():
                CCTree._inject_file_name(child, file_name)

    def save_json(self, path: str) -> None:
        """Saves the tree to a JSON file.

        Args:
            path (str): The path to the output JSON file.
        """
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "CCTree":
        """Loads a tree from a JSON file.

        Args:
            path (str): The path to the input JSON file.

        Returns:
            CCTree: The loaded CCTree instance.
        """
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        return CCTree.from_dict(obj)

    def get_structure(self) -> dict[str, Any]:
        """Gets the skeletal structure of the entire tree.

        Returns:
            dict[str, Any]: The skeletal structure representation.
        """
        return self.root.get_structure()

    def get_clean_structure(self) -> dict[str, Any]:
        """Gets the simplified structure of the entire tree.

        Returns:
            dict[str, Any]: The simplified structure representation.
        """
        return self.root.get_clean_structure()

    def find_node_by_path(self, path: str) -> CCTreeNode | None:
        """Finds a node by its path string.

        Args:
            path (str): The path string, e.g., "Root--Child1--GrandChild1".

        Returns:
            CCTreeNode | None: The found node, or None if not found.
        """
        parts = path.split("--")
        if not parts:
            return None

        current = self.root
        # Compatibility handling: if the path has only one part and matches the root, return directly.
        if len(parts) == 1:
            return current

        # Attempt to search layer by layer.
        for part in parts[1:]:
            if part in current.children:
                current = current.children[part]
            else:
                return None
        return current

    def update_impact(self, path: str) -> dict[str, int]:
        """Updates the impact values of nodes along the path.

        - Intermediate nodes on the path: impact + 1
        - Target leaf node: impact + 2

        Args:
            path: The path of the nodes to update.

        Returns:
            A mapping of updated {path: impact}.
        """
        parts = path.split("--")
        if not parts:
            return {}

        impact_updates = {}
        current = self.root
        current_path = parts[0]

        # Root node processing (+1)
        current.impact += 1
        impact_updates[current_path] = current.impact

        # Update layer by layer downwards
        for i, part in enumerate(parts[1:]):
            if part in current.children:
                current = current.children[part]
                current_path += f"--{part}"

                # Check if it is the last node (target node)
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
    """A collection of retrieval results.

    Encapsulates the hit text and corresponding location information during the retrieval process.

    Attributes:
        text_map: Mapping from path to text content. Key is the node path, Value is the text of the node. Used for LLM reasoning.
        locations: List of hit locations. Contains Location information for all hit nodes, used for screenshots or highlighting.
    """

    text_map: Dict[str, str] = field(default_factory=dict)
    locations: List[Location] = field(default_factory=list)

    def update(self, other: "RetrievalResult") -> None:
        """Merges another retrieval result.

        Args:
            other: The RetrievalResult object to be merged.
        """
        self.text_map.update(other.text_map)
        self.locations.extend(other.locations)
