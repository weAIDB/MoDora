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
