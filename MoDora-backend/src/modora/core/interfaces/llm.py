from typing import Protocol, Tuple


class LLMClient(Protocol):
    """
    LLM 客户端接口协议。
    定义了与大语言模型交互以生成标注的标准接口。
    """

    def generate_annotation(
        self, base64_image: str, cp_type: str
    ) -> Tuple[str, str, str]:
        """
        为图片组件生成标注信息。

        Args:
            base64_image: Base64 编码的图片字符串
            cp_type: 组件类型 (如 'image', 'chart', 'table')

        Returns:
            Tuple[str, str, str]: 包含 (标题, 元数据, 内容) 的元组
        """
        ...

    def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        """
        为标题列表生成标题层次结构。

        Args:
            title_list: 标题列表
            base64_image: Base64 编码的图片

        Returns:
            str: 标题层次结构
        """
        ...


class AsyncLLMClient(Protocol):
    """
    异步 LLM 客户端接口协议。
    """

    async def generate_text(self, prompt: str) -> str:
        ...

    async def generate_levels(self, title_list: list[str], base64_image: str) -> str:
        ...

    async def generate_metadata(self, data: str, num: int) -> str:
        ...

    async def integrate_metadata(self, data: str, num: int) -> str:
        ...

    async def parse_question(self, query: str) -> str:
        ...

    async def select_children(
        self, keys: list[str], query: str, path: str, metadata_map: str
    ) -> str:
        ...

    async def check_node(self, data: str, query: str) -> bool:
        ...

    async def check_node_mm(self, data: str, base64_image: str, query: str) -> bool:
        ...

    async def check_answer(self, query: str, answer: str) -> bool:
        ...

    async def reason_retrieved(self, query: str, schema: str, evidence: str) -> str:
        ...

    async def reason_whole(self, query: str, data: str) -> str:
        ...

    async def generate_annotation_async(
        self, base64_image: str, cp_type: str, settings: object | None = None
    ) -> Tuple[str, str, str]:
        ...
