from __future__ import annotations

import ast
import logging

from modora.core.domain.component import ComponentPack
from modora.core.settings import Settings
from modora.core.interfaces.llm import LLMClient
from modora.core.interfaces.media import ImageProvider


class LevelGenerator:
    def __init__(self, llm_client: LLMClient, image_provider: ImageProvider):
        self.llm = llm_client
        self.media = image_provider

    def _get_title_level(self, title: str) -> int:
        """
        从标题中提取级别
        """
        level = 0
        for char in title.lstrip():
            if char == "#":
                level += 1
            else:
                break
        return level

    def generate_level(
        self,
        source_path: str,
        cp: ComponentPack,
        config: Settings,
        logger: logging.Logger,
    ) -> list[str]:
        """
        生成标题层次结构
        """
        text_components = [co for co in cp.body if co.type == "text"]
        title_list = [co.title for co in text_components]
        title_bbox_list = [co.location[0] for co in text_components]
        image = self.media.crop_image(source_path, title_bbox_list)

        try:
            leveled_title = self.llm.generate_levels(title_list, image)
            leveled_title = ast.literal_eval(leveled_title)
        except Exception as e:
            logger.warning(f"generate_levels failed: {e}")
            leveled_title = []

        for co, title in zip(text_components, leveled_title):
            co.title_level = self._get_title_level(title)

        return cp
