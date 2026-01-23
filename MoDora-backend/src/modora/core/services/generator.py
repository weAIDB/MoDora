from __future__ import annotations

import logging
import math

from modora.core.domain.cctree import CCTree, CCTreeNode
from modora.core.infra.llm.qwen import AsyncQwenLLMClient


class AsyncMetadataGenerator:
    def __init__(
        self,
        n0: int,
        growth_rate: float,
        llm_client: AsyncQwenLLMClient,
        logger: logging.Logger,
    ):
        self.llm = llm_client
        self.logger = logger
        self.n0 = n0  # 叶子节点关键词数量
        self.growth_rate = growth_rate  # 子节点关键词数量增长率

    def _calculate_keyword_cnt(self, node: CCTreeNode, growth_rate: float = 2.0) -> int:
        """计算节点的关键词数量"""
        if not node.children:
            return self.n0
        total_child_keyword_cnt = sum(
            child.keyword_cnt for child in node.children.values()
        )
        log_part = math.log2(pow(total_child_keyword_cnt, growth_rate))
        fraction_part = (node.depth + node.height - 1) / node.depth
        keyword_cnt = math.ceil(fraction_part + log_part + 1)
        return keyword_cnt

    async def _generate_metadata(self, node: CCTreeNode, cnt: int) -> None:
        try:
            node.metadata = await self.llm.generate_metadata(node.data, cnt)
        except Exception as e:
            self.logger.warning(
                "generate metadata failed for text node", extra={"error": str(e)}
            )

    async def _integrate_metadata(self, node: CCTreeNode, cnt: int) -> None:
        children = list(node.children.values())
        if not children:
            return
        base_metadata = node.metadata or ""
        child_metadata = [child.metadata or "" for child in children]
        all_metadata = [base_metadata, *child_metadata]
        try:
            node.metadata = await self.llm.integrate_metadata(all_metadata, cnt)
        except Exception as e:
            self.logger.warning(
                "integrate metadata failed for text node", extra={"error": str(e)}
            )

    async def _get_node_metadata(self, node: CCTreeNode, cnt: int) -> None:
        if node.type == "text":
            await self._generate_metadata(node, cnt)
            await self._integrate_metadata(node, cnt)
        elif node.type == "root":
            await self._integrate_metadata(node, cnt)
        elif node.metadata is None or node.metadata == "":
            node.metadata = node.data

    async def _dfs(self, node: CCTreeNode, parent: CCTreeNode | None = None) -> None:
        if parent is not None:
            node.depth = parent.depth + 1
        for child in list(node.children.values()):
            await self._dfs(child, node)
            node.height = max(node.height, child.height + 1)
        node.keyword_cnt = self._calculate_keyword_cnt(node, self.growth_rate)
        await self._get_node_metadata(node, node.keyword_cnt)

    async def get_metadata(self, cctree: CCTree) -> None:
        """获取组件树的元数据"""
        await self._dfs(cctree.root, None)
