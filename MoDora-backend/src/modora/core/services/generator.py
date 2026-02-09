from __future__ import annotations

import logging
import math

from modora.core.domain import CCTree, CCTreeNode
from modora.core.infra.llm import BaseAsyncLLMClient


class AsyncMetadataGenerator:
    """
    异步元数据生成器，负责为 CCTree 节点生成语义关键词。
    """

    def __init__(
        self,
        n0: int,
        growth_rate: float,
        llm_client: BaseAsyncLLMClient,
        logger: logging.Logger,
    ):
        self.llm = llm_client
        self.logger = logger
        self.n0 = n0  # 叶子节点关键词数量
        self.growth_rate = growth_rate  # 子节点关键词数量增长率

    def _calculate_keyword_cnt(self, node: CCTreeNode, growth_rate: float = 2.0) -> int:
        """
        计算节点的关键词目标数量。

        基于节点的深度、高度以及子节点的关键词总量，通过对数增长模型计算。
        """
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
        """为文本节点生成基础元数据（关键词）。"""
        try:
            node.metadata = await self.llm.generate_metadata(node.data, cnt)
        except Exception as e:
            self.logger.warning(
                "generate metadata failed for text node", extra={"error": str(e)}
            )

    async def _integrate_metadata(self, node: CCTreeNode, cnt: int) -> None:
        """将当前节点和子节点的元数据进行整合，生成更高级别的摘要。"""
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
        """根据节点类型获取或生成元数据。"""
        if node.type == "text":
            # 文本节点：先生成，再整合子节点信息
            await self._generate_metadata(node, cnt)
            await self._integrate_metadata(node, cnt)
        elif node.type == "root":
            # 根节点：仅整合子节点信息
            await self._integrate_metadata(node, cnt)
        elif node.metadata is None or node.metadata == "":
            # 其他节点：默认使用原始数据
            node.metadata = node.data

    async def _dfs(self, node: CCTreeNode, parent: CCTreeNode | None = None) -> None:
        """深度优先遍历，从叶子节点向上生成元数据。"""
        if parent is not None:
            node.depth = parent.depth + 1

        # 递归处理子节点
        for child in list(node.children.values()):
            await self._dfs(child, node)
            node.height = max(node.height, child.height + 1)

        # 计算当前节点的关键词数量并生成元数据
        node.keyword_cnt = self._calculate_keyword_cnt(node, self.growth_rate)
        await self._get_node_metadata(node, node.keyword_cnt)

    async def get_metadata(self, cctree: CCTree) -> None:
        """
        获取组件树的元数据。

        通过 DFS 遍历整个树，利用 LLM 为每个节点生成语义化的元数据摘要。
        """
        await self._dfs(cctree.root, None)
