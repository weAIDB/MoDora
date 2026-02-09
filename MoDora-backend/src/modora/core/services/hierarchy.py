from __future__ import annotations

import ast
import asyncio
import logging

from modora.core.domain.component import ComponentPack
from modora.core.settings import Settings
<<<<<<< HEAD
from modora.core.infra.llm.local import AsyncLocalLLMClient
=======
from modora.core.interfaces.llm import LLMClient
from modora.core.infra.llm.base import BaseAsyncLLMClient
>>>>>>> api
from modora.core.interfaces.media import ImageProvider


class AsyncLevelGenerator:
<<<<<<< HEAD
    """
    异步层级生成器，负责利用 LLM 纠正或生成标题的层级结构（Markdown 风格）。
    """

    def __init__(self, llm_client: AsyncLocalLLMClient, image_provider: ImageProvider):
=======
    def __init__(self, llm_client: BaseAsyncLLMClient, image_provider: ImageProvider):
>>>>>>> api
        self.llm = llm_client
        self.media = image_provider

    def _get_title_level(self, title: str) -> int:
        """从带有 # 的标题字符串中解析出层级深度（例如 ### 标题 -> 3）。"""
        level = 0
        for char in title.lstrip():
            if char == "#":
                level += 1
            else:
                break
        return level if level > 0 else 1

    async def generate_level(
        self,
        source_path: str,
        cp: ComponentPack,
        config: Settings,
        logger: logging.Logger,
    ) -> ComponentPack:
        """
        利用 LLM 为组件包中的文本标题生成或纠正层级信息。

        参数:
            source_path: PDF 源文件路径。
            cp: 待处理的组件包。
            config: 系统配置。
            logger: 日志实例。

        返回:
            ComponentPack: 更新了 title_level 的组件包。
        """
        text_components = [co for co in cp.body if co.type == "text"]
        located = [co for co in text_components if co.location]
        if not located:
            return cp

        # 准备待处理的标题列表和对应的位置信息
        title_list = [co.title for co in located]
        title_bbox_list = [co.location[0] for co in located]

        # 裁剪标题区域的图像，辅助 LLM 进行视觉层级判断
        image = self.media.crop_image(source_path, title_bbox_list)

        leveled_title: list[str] = []
        max_attempts = 3
        # 带有重试机制的 LLM 调用
        for attempt in range(1, max_attempts + 1):
            try:
                # 调用本地多模态 LLM 生成带有 Markdown 层级的标题
                raw = await self.llm.generate_levels(title_list, image)
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, list):
                    leveled_title = [str(x) for x in parsed]
                    break
                raise TypeError("generate_levels result is not a list")
            except Exception as e:
                logger.warning(
                    f"generate_levels failed (attempt {attempt}/{max_attempts}) for {source_path}: {e}"
                )
                leveled_title = []
                if attempt < max_attempts:
                    await asyncio.sleep(0.2 * attempt)

        # 将生成的层级信息回填到组件中
        for co, title in zip(located, leveled_title):
            co.title_level = self._get_title_level(title)

        return cp
