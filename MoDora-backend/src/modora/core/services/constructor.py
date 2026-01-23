from __future__ import annotations

import logging

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.domain.component import Component, ComponentPack, TITLE
from modora.core.interfaces.llm import LLMClient
from modora.core.interfaces.media import ImageProvider
from modora.core.settings import Settings
from modora.core.services.hierarchy import LevelGenerator


class TreeConstructor:
    def __init__(self, config: Settings, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def construct_tree(self, cp: ComponentPack) -> CCTree:
        """从组件包构造组件树。"""
        root = CCTreeNode(type="root", metadata="", data="", location=[], children={})
        stack: list[tuple[CCTreeNode, int]] = [(root, -1)]

        def _uniq_key(parent: CCTreeNode, title: str) -> str:
            base = (title or TITLE).strip() or TITLE
            if base not in parent.children:
                return base
            cnt = 1
            while f"{base}_{cnt}" in parent.children:
                cnt += 1
            return f"{base}_{cnt}"

        for component in cp.body:
            node = CCTreeNode.from_component(component)

            if component.type == "text":
                level = int(getattr(component, "title_level", 1) or 1)
                while stack and stack[-1][1] >= level:
                    stack.pop()
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                stack.append((node, level))
                continue

            if component.type in {"image", "table", "chart"}:
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                continue

            parent = stack[-1][0] if stack else root
            key = _uniq_key(parent, getattr(component, "title", "") or component.type)
            parent.children[key] = node

        def _supp_node(co: Component) -> CCTreeNode:
            data = str(co.data or "")
            return CCTreeNode(
                type=str(co.type or ""),
                metadata=data,
                data=data,
                location=list(co.location or []),
                children={},
            )

        header_children = {
            f"Header of Page {p}": _supp_node(co) for p, co in cp.supplement.header.items()
        }
        footer_children = {
            f"Footer of Page {p}": _supp_node(co) for p, co in cp.supplement.footer.items()
        }
        number_children = {
            f"Original number of Page {p}": _supp_node(co)
            for p, co in cp.supplement.number.items()
        }
        aside_children = {
            f"Aside text of Page {p}": _supp_node(co) for p, co in cp.supplement.aside.items()
        }

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

    def build_tree(
        self,
        source_path: str,
        cp: ComponentPack,
        llm: LLMClient,
        media: ImageProvider,
    ) -> CCTree:
        cp = LevelGenerator(llm, media).generate_level(
            source_path=source_path, cp=cp, config=self.config, logger=self.logger
        )
        return self.construct_tree(cp)
