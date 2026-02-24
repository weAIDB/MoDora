import ast
import asyncio
import logging

from modora.core.settings import Settings
from modora.core.domain import CCTree, CCTreeNode, RetrievalResult
from modora.core.prompts import select_children_prompt
from modora.core.infra.llm import AsyncLLMFactory
from modora.core.infra.pdf import PDFCropper

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """CCTree retriever based on semantic understanding."""

    def __init__(
        self,
        settings: Settings | None = None,
        instance_id: str | None = None,
    ):
        self.settings = settings or Settings.load()
        self.llm = AsyncLLMFactory.create(
            self.settings, instance_id=instance_id
        )
        self.cropper = PDFCropper()

    async def retrieve(
        self,
        tree: CCTree,
        query: str,
        source_path: str | dict[str, str],
    ) -> RetrievalResult:
        """Recursively retrieves relevant nodes from the CCTree.

        Args:
            tree (CCTree): CCTree instance (potentially a merged multi-document tree).
            query (str): User query string.
            source_path (str | dict[str, str]): Path to the PDF file, or a mapping from filenames to paths for multi-document trees.

        Returns:
            RetrievalResult: Retrieval results.
        """
        # Start from the root node
        nodes = {"root": tree.root}
        return await self._retrieve_recursive(nodes, query, source_path)

    async def _retrieve_recursive(
        self,
        nodes: dict[str, CCTreeNode],
        query: str,
        source_path: str | dict[str, str],
    ) -> RetrievalResult:
        """Internal recursive method to process nodes level by level.

        Args:
            nodes (dict[str, CCTreeNode]): Dictionary of nodes to process.
            query (str): User query string.
            source_path (str | dict[str, str]): Path to the source file or mapping.

        Returns:
            RetrievalResult: The accumulated retrieval results.
        """
        result = RetrievalResult()

        if not nodes:
            return result

        # 1. Process the current level
        current_result, next_level_nodes = await self._process_level(
            nodes, query, source_path
        )
        result.update(current_result)

        # 2. Process the next level (recursive)
        if next_level_nodes:
            next_level_result = await self._retrieve_recursive(
                next_level_nodes, query, source_path
            )
            result.update(next_level_result)

        return result

    async def _process_level(
        self,
        nodes: dict[str, CCTreeNode],
        query: str,
        source_path: str | dict[str, str],
    ):
        """Process a batch of nodes concurrently.

        Args:
            nodes (dict[str, CCTreeNode]): Dictionary of nodes to process.
            query (str): User query string.
            source_path (str | dict[str, str]): Path to the source file or mapping.

        Returns:
            tuple[RetrievalResult, dict[str, CCTreeNode]]: A tuple containing the
                retrieval results and the next level of nodes to process.
        """
        result = RetrievalResult()
        selected_children_next_level = {}

        tasks = []
        for path, node in nodes.items():
            # Determine the correct source_path for the current node
            current_source = source_path
            if isinstance(source_path, dict):
                # Path format is usually root--filename--...
                parts = path.split("--")
                if len(parts) > 1:
                    file_name = parts[1]
                    current_source = source_path.get(file_name, "")
                    # Ensure file_name in node.location is set (just in case)
                    if node.location:
                        for loc in node.location:
                            if not loc.file_name:
                                loc.file_name = file_name

            tasks.append(self._process_single_node(path, node, query, current_source))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Error processing node during retrieval: {res}")
                continue

            sub_result, sub_selected_children = res
            result.update(sub_result)
            selected_children_next_level.update(sub_selected_children)

        return result, selected_children_next_level

    async def _process_single_node(
        self, path: str, node: CCTreeNode, query: str, source_path: str
    ):
        """Process a single node: check relevance and select child nodes.

        Args:
            path (str): The node path.
            node (CCTreeNode): The node to process.
            query (str): User query string.
            source_path (str): Path to the source file.

        Returns:
            tuple[RetrievalResult, dict[str, CCTreeNode]]: A tuple containing the
                retrieval results and the selected child nodes.
        """
        result = RetrievalResult()
        selected_children = {}

        try:
            # Check relevance (asynchronous)
            if node.has_content() and await self._is_relevant(
                node, path, source_path, query
            ):
                if node.data:
                    result.text_map[path] = node.data
                if node.location:
                    result.locations.extend(node.location)
                    result.locations_by_path.setdefault(path, []).extend(node.location)

            # If child nodes exist, perform selection
            if node.children:
                title_list = await self._select_children(node, query, path)
                self._get_children(title_list, selected_children, node, path)

        except Exception as e:
            logger.error(f"Retrieval crashed on node {path}: {e}")

        return result, selected_children

    async def _is_relevant(
        self, node: CCTreeNode, path: str, source_path: str, query: str
    ) -> bool:
        """Check if a node is relevant to the query using LLM and image content.

        Args:
            node (CCTreeNode): The node to check.
            path (str): The node path.
            source_path (str): Path to the source file.
            query (str): User query string.

        Returns:
            bool: True if the node is relevant, False otherwise.
        """
        base_path = path.split("--")[-1] if "--" in path else path
        titled_data = base_path + ":" + node.data

        # Run PDF cropping in executor as it involves blocking IO/CPU operations
        loop = asyncio.get_running_loop()
        try:
            image = await loop.run_in_executor(
                None, self.cropper.crop_image, source_path, node.location
            )
        except Exception as e:
            logger.error(f"Error cropping image for node {path}: {e}")
            return False

        # check_node_mm returns a boolean directly in BaseAsyncLLMClient
        return await self.llm.check_node_mm(titled_data, query, image)

    async def _select_children(
        self, node: CCTreeNode, query: str, path: str
    ) -> list[str]:
        """Select relevant child nodes using LLM.

        Args:
            node (CCTreeNode): The parent node.
            query (str): User query string.
            path (str): The node path.

        Returns:
            list[str]: A list of selected child node titles.
        """
        metadata_map = node.get_metadata_map()
        children_list = list(node.children.keys())

        prompt = select_children_prompt.format(
            query=query, list=children_list, path=path, metadata_map=metadata_map
        )

        res = await self.llm.generate_text(prompt)

        title_list = []
        try:
            title_list = ast.literal_eval(res)
            if not isinstance(title_list, list):
                logger.warning(f"LLM returned non-list for select_children: {res}")
                title_list = []
        except Exception as e:
            logger.warning(
                f"Error parsing select_children response: {e}, Response: {res}"
            )
            title_list = []

        logger.info(
            f"Select Children : {title_list}", extra={"path": path, "query": query}
        )
        return title_list

    def _get_children(
        self,
        title_list: list[str],
        selected_children: dict,
        node: CCTreeNode,
        path: str,
    ):
        """
        Populate selected_children dictionary based on titles selected by LLM.
        """
        for title in title_list:
            if title not in node.children:
                logger.warning(f"Title {title} not found in node children")
                continue
            cur_path = path + "--" + title
            selected_children[cur_path] = node.children[title]
