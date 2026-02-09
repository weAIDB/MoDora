from __future__ import annotations

import logging

from modora.core.domain import CCTree, CCTreeNode, Component, ComponentPack, TITLE
from modora.core.settings import Settings


class TreeConstructor:
    """
    负责将 ComponentPack 转换为 CCTree 结构的构造器。
    """

    def __init__(self, config: Settings, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def construct_tree(self, cp: ComponentPack) -> CCTree:
        """
        从组件包构造组件树。

        参数:
            cp: 包含文档所有组件的 ComponentPack。

        返回:
            CCTree: 构造完成的组件树。
        """
        root = CCTreeNode(type="root", metadata="", data="", location=[], children={})
        stack: list[tuple[CCTreeNode, int]] = [(root, -1)]

        def _uniq_key(parent: CCTreeNode, title: str) -> str:
            """生成唯一的子节点键名，处理同名标题。"""
            base = (title or TITLE).strip() or TITLE
            if base not in parent.children:
                return base
            cnt = 1
            while f"{base}_{cnt}" in parent.children:
                cnt += 1
            return f"{base}_{cnt}"

        # 1. 处理正文组件 (cp.body)
        for component in cp.body:
            node = CCTreeNode.from_component(component)

            if component.type == "text":
                # 处理文本节点的层级关系（基于 title_level）
                level = int(getattr(component, "title_level", 1) or 1)
                while stack and stack[-1][1] >= level:
                    stack.pop()
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                stack.append((node, level))
                continue

            # 处理非文本节点（图片、表格、图表等）
            if component.type in {"image", "table", "chart"}:
                parent = stack[-1][0] if stack else root
                key = _uniq_key(parent, component.title)
                parent.children[key] = node
                continue

            # 处理其他类型的节点
            parent = stack[-1][0] if stack else root
            key = _uniq_key(parent, getattr(component, "title", "") or component.type)
            parent.children[key] = node

        def _supp_node(co: Component) -> CCTreeNode:
            """将辅助组件转换为树节点。"""
            data = str(co.data or "")
            return CCTreeNode(
                type=str(co.type or ""),
                metadata=data,
                data=data,
                location=list(co.location or []),
                children={},
            )

        # 2. 处理补充信息 (cp.supplement)
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

        # 构造补充信息的各个分类根节点
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

        # 汇总所有补充信息到 supplement 节点
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
