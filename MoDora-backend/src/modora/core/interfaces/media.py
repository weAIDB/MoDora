from typing import Protocol

from modora.core.domain.component import Component


class ImageProvider(Protocol):
    """
    图片提供者接口协议。
    定义了从源文件（如 PDF）中获取图片数据的标准接口。
    """

    def crop_image(self, source: str, component: Component) -> str:
        """
        根据组件的位置信息从源文件中裁剪图片。

        Args:
            source: 源文件路径或标识符
            component: 包含位置信息的组件对象

        Returns:
            str: Base64 编码的图片字符串
        """
        ...
