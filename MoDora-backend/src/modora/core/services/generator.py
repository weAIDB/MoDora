from __future__ import annotations

import logging
import math

from modora.core.domain import CCTree, CCTreeNode
from modora.core.infra.llm import BaseAsyncLLMClient


class AsyncMetadataGenerator:
    """Asynchronous metadata generator.

    Responsible for generating semantic keywords for CCTree nodes.
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
        self.n0 = n0  # Number of keywords for leaf nodes
        self.growth_rate = growth_rate  # Growth rate of keywords for child nodes

    def _calculate_keyword_cnt(self, node: CCTreeNode, growth_rate: float = 2.0) -> int:
        """Calculates the target number of keywords for a node.

        Based on the node's depth, height, and the total keywords of child nodes,
        calculated using a logarithmic growth model.
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
        """Generates basic metadata (keywords) for a text node."""
        try:
            node.metadata = await self.llm.generate_metadata(node.data, cnt)
        except Exception as e:
            self.logger.warning(
                "generate metadata failed for text node", extra={"error": str(e)}
            )

    async def _integrate_metadata(self, node: CCTreeNode, cnt: int) -> None:
        """Integrates metadata from the current node and its children to generate a higher-level summary."""
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
        """Retrieves or generates metadata based on the node type."""
        if node.type == "text":
            # Text node: generate first, then integrate child node information
            await self._generate_metadata(node, cnt)
            await self._integrate_metadata(node, cnt)
        elif node.type == "root":
            # Root node: integrate child node information only
            await self._integrate_metadata(node, cnt)
        elif node.metadata is None or node.metadata == "":
            # Other nodes: use original data by default
            node.metadata = node.data

    async def _dfs(self, node: CCTreeNode, parent: CCTreeNode | None = None) -> None:
        """Depth-first traversal, generating metadata from leaf nodes upwards."""
        if parent is not None:
            node.depth = parent.depth + 1

        # Recursively process child nodes
        for child in list(node.children.values()):
            await self._dfs(child, node)
            node.height = max(node.height, child.height + 1)

        # Calculate keyword count for the current node and generate metadata
        node.keyword_cnt = self._calculate_keyword_cnt(node, self.growth_rate)
        await self._get_node_metadata(node, node.keyword_cnt)

    async def get_metadata(self, cctree: CCTree) -> None:
        """Retrieves metadata for the component tree.

        Traverses the entire tree via DFS, using LLM to generate semantic metadata summaries for each node.
        """
        await self._dfs(cctree.root, None)
