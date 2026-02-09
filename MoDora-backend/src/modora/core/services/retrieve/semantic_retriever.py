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
    """
    基于语义理解的 CCTree 检索器。
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.llm = AsyncLLMFactory.create(self.settings, mode="local")
        self.cropper = PDFCropper()

    async def retrieve(
        self, tree: CCTree, query: str, source_path: str
    ) -> RetrievalResult:
        """
        递归地从 CCTree 中检索相关节点。

        参数:
            tree: CCTree 实例。
            query: 用户查询字符串。
            source_path: PDF 文件路径。

        返回:
            RetrievalResult: 检索结果。
        """
        # 从根节点开始
        nodes = {"root": tree.root}
        return await self._retrieve_recursive(nodes, query, source_path)

    async def _retrieve_recursive(
        self, nodes: dict[str, CCTreeNode], query: str, source_path: str
    ) -> RetrievalResult:
        """
        内部递归方法，逐层处理节点。
        """
        result = RetrievalResult()

        if not nodes:
            return result

        # 1. 处理当前层级
        current_result, next_level_nodes = await self._process_level(
            nodes, query, source_path
        )
        result.update(current_result)

        # 2. 处理下一层级（递归）
        if next_level_nodes:
            next_level_result = await self._retrieve_recursive(
                next_level_nodes, query, source_path
            )
            result.update(next_level_result)

        return result

    async def _process_level(
        self, nodes: dict[str, CCTreeNode], query: str, source_path: str
    ):
        """
        并发处理一批节点。
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
                logger.error(f"检索过程中处理节点出错: {res}")
                continue

            sub_result, sub_selected_children = res
            result.update(sub_result)
            selected_children_next_level.update(sub_selected_children)

        return result, selected_children_next_level

    async def _process_single_node(
        self, path: str, node: CCTreeNode, query: str, source_path: str
    ):
        """
        处理单个节点：检查相关性并选择子节点。
        """
        result = RetrievalResult()
        selected_children = {}

        try:
            # 检查相关性（异步）
            if node.has_content() and await self._is_relevant(
                node, path, source_path, query
            ):
                if node.data:
                    result.text_map[path] = node.data
                # 语义匹配意味着整个节点都是相关的
                result.locations.extend(node.location)

            # 如果存在子节点，则进行选择
            if node.children:
                title_list = await self._select_children(node, query, path)
                self._get_children(title_list, selected_children, node, path)

        except Exception as e:
            logger.error(f"节点 {path} 上的检索崩溃: {e}")

        return result, selected_children

    async def _is_relevant(
        self, node: CCTreeNode, path: str, source_path: str, query: str
    ) -> bool:
        """
        使用 LLM 和图像内容检查节点是否与查询相关。
        """
        base_path = path.split("--")[-1] if "--" in path else path
        titled_data = base_path + ":" + node.data

        # 在 executor 中运行 PDF 裁剪，因为它涉及阻塞的 IO/CPU 操作
        loop = asyncio.get_running_loop()
        try:
            image = await loop.run_in_executor(
                None, self.cropper.crop_image, source_path, node.location
            )
        except Exception as e:
            logger.error(f"为节点 {path} 裁剪图像出错: {e}")
            return False

        # check_node_mm 在 BaseAsyncLLMClient 中直接返回布尔值
        return await self.llm.check_node_mm(titled_data, image, query)

    async def _select_children(
        self, node: CCTreeNode, query: str, path: str
    ) -> list[str]:
        """
        使用 LLM 选择相关的子节点。
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
