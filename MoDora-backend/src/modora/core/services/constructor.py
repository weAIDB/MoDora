from __future__ import annotations

import logging

from modora.core.domain import CCTree, CCTreeNode, Component, ComponentPack, TITLE
from modora.core.settings import Settings


class TreeConstructor:
    """Constructor responsible for converting a ComponentPack into a CCTree structure."""

    def __init__(self, config: Settings, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def construct_tree(self, cp: ComponentPack) -> CCTree:
        """Constructs a component tree from a component pack.

        Args:
            cp (ComponentPack): The component pack containing all document components.

        Returns:
            CCTree: The constructed component tree.
        """
        root = CCTreeNode(type="root", metadata="", data="", location=[], children={})
        stack: list[tuple[CCTreeNode, int]] = [(root, -1)]

        def _uniq_key(parent: CCTreeNode, title: str) -> str:
            """Generates a unique child node key name, handling duplicate titles."""
            base = (title or TITLE).strip() or TITLE
            if base not in parent.children:
                return base
            cnt = 1
            while f"{base}_{cnt}" in parent.children:
                cnt += 1
            return f"{base}_{cnt}"

        # 1. Process body components (cp.body)
        for component in cp.body:
            node = CCTreeNode.from_component(component)

            if component.type == "text":
                # Handle hierarchical relationships of text nodes (based on title_level)
                level = int(getattr(component, "title_level", 1) or 1)
                while stack and stack[-1][1] >= level:
                    stack.pop()
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                stack.append((node, level))
                continue

            # Handle non-text nodes (images, tables, charts, etc.)
            if component.type in {"image", "table", "chart"}:
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                continue

            # Handle other types of nodes
            parent = stack[-1][0] if stack else root
            key = _uniq_key(parent, getattr(component, "title", "") or component.type)
            parent.children[key] = node

        def _supp_node(co: Component) -> CCTreeNode:
            """Converts a supplementary component into a tree node."""
            data = str(co.data or "")
            return CCTreeNode(
                type=str(co.type or ""),
                metadata=data,
                data=data,
                location=list(co.location or []),
                children={},
            )

        # 2. Process supplementary information (cp.supplement)
        header_children = {
            f"Header of Page {p}": _supp_node(co)
            for p, co in cp.supplement.header.items()
        }
        footer_children = {
            f"Footer of Page {p}": _supp_node(co)
            for p, co in cp.supplement.footer.items()
        }
        number_children = {
            f"Original number of Page {p}": _supp_node(co)
            for p, co in cp.supplement.number.items()
        }
        aside_children = {
            f"Aside text of Page {p}": _supp_node(co)
            for p, co in cp.supplement.aside.items()
        }

        # Construct root nodes for each category of supplementary information
        header_root = CCTreeNode(
            type="header",
            metadata="Record header information in the document",
            data="",
            location=[],
            children=header_children,
        )
        footer_root = CCTreeNode(
            type="footer",
            metadata="Record footer information in the document",
            data="",
            location=[],
            children=footer_children,
        )
        number_root = CCTreeNode(
            type="number",
            metadata="Record original number of pages in the document",
            data="",
            location=[],
            children=number_children,
        )
        aside_root = CCTreeNode(
            type="aside_text",
            metadata="Record aside text in the document",
            data="",
            location=[],
            children=aside_children,
        )

        # Consolidate all supplementary information into the supplement node
        supplement_root = CCTreeNode(
            type="supplement",
            metadata=(
                "Record supplement information like header, footer, original page number and aside text in the document"
            ),
            data="",
            location=[],
            children={
                "header": header_root,
                "footer": footer_root,
                "number": number_root,
                "aside": aside_root,
            },
        )
        root.children["Supplement"] = supplement_root

        return CCTree(root=root)
