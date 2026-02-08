import ast
import asyncio
import logging

from modora.core.settings import Settings
from modora.core.domain.cctree import CCTree, CCTreeNode, RetrievalResult
from modora.core.prompts.retrieval import select_children_prompt
from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.pdf.cropper import PDFCropper

logger = logging.getLogger(__name__)

class SemanticRetriever:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.llm = AsyncLLMFactory.create(self.settings, mode="local")
        self.cropper = PDFCropper()
    
    async def retrieve(self, tree: CCTree, query: str, source_path: str) -> RetrievalResult:
        """
        Recursively retrieve relevant nodes from the CCTree.
        """
        # Start from the root node
        nodes = {"root": tree.root}
        return await self._retrieve_recursive(nodes, query, source_path)

    async def _retrieve_recursive(self, nodes: dict[str, CCTreeNode], query: str, source_path: str) -> RetrievalResult:
        """
        Internal recursive method to process nodes level by level.
        """
        result = RetrievalResult()
        
        if not nodes:
            return result

        # 1. Process current level
        current_result, next_level_nodes = await self._process_level(nodes, query, source_path)
        result.update(current_result)
        
        # 2. Process next level (Recursion)
        if next_level_nodes:
            next_level_result = await self._retrieve_recursive(next_level_nodes, query, source_path)
            result.update(next_level_result)
            
        return result

    async def _process_level(self, nodes: dict[str, CCTreeNode], query: str, source_path: str):
        """
        Process a batch of nodes concurrently.
        """
        result = RetrievalResult()
        selected_children_next_level = {}
        
        tasks = [
            self._process_single_node(path, node, query, source_path)
            for path, node in nodes.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Error processing node in retrieve: {res}")
                continue
            
            sub_result, sub_selected_children = res
            result.update(sub_result)
            selected_children_next_level.update(sub_selected_children)
            
        return result, selected_children_next_level

    async def _process_single_node(self, path: str, node: CCTreeNode, query: str, source_path: str):
        """
        Process a single node: check relevance and select children.
        """
        result = RetrievalResult()
        selected_children = {}

        try:
            # Check relevance (async)
            if node.has_content() and await self._is_relevant(node, path, source_path, query):
                if node.data:
                    result.text_map[path] = node.data
                result.locations.extend(node.location) # Semantic match implies whole node is relevant

            # Select children if present
            if node.children:
                title_list = await self._select_children(node, query, path)
                self._get_children(title_list, selected_children, node, path)
        
        except Exception as e:
            logger.error(f"Retrieve on node {path} crash: {e}")

        return result, selected_children

    async def _is_relevant(self, node: CCTreeNode, path: str, source_path: str, query: str) -> bool:
        """
        Check if the node is relevant to the query using LLM and image content.
        """
        base_path = path.split('--')[-1] if '--' in path else path
        titled_data = base_path + ":" + node.data
        
        # Run PDF cropping in executor as it involves blocking IO/CPU operations
        loop = asyncio.get_running_loop()
        try:
            image = await loop.run_in_executor(None, self.cropper.crop_image, source_path, node.location)
        except Exception as e:
            logger.error(f"Error cropping image for node {path}: {e}")
            return False

        # check_node_mm returns bool directly in BaseAsyncLLMClient
        return await self.llm.check_node_mm(titled_data, image, query)

    async def _select_children(self, node: CCTreeNode, query: str, path: str) -> list[str]:
        """
        Use LLM to select relevant children nodes.
        """
        metadata_map = node.get_metadata_map()
        children_list = list(node.children.values())
        
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
            logger.warning(f"Error parsing select_children response: {e}, Response: {res}")
            title_list = []
            
        logger.info(f'Select Children : {title_list}', extra={'path': path, 'query': query})
        return title_list

    def _get_children(self, title_list: list[str], selected_children: dict, node: CCTreeNode, path: str):
        """
        Populate selected_children dictionary based on titles selected by LLM.
        """
        for title in title_list:
            if title not in node.children:
                logger.warning(f"Title {title} not found in node children")
                continue
            cur_path = path + '--' + title
            selected_children[cur_path] = node.children[title]
