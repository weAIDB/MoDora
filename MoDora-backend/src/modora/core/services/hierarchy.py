from __future__ import annotations

import ast
import asyncio
import logging

from modora.core.domain.component import ComponentPack
from modora.core.settings import Settings
from modora.core.interfaces.llm import LLMClient
from modora.core.infra.llm.qwen import AsyncQwenLLMClient
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
        return level if level > 0 else 1

    def generate_level(
        self,
        source_path: str,
        cp: ComponentPack,
        config: Settings,
        logger: logging.Logger,
    ) -> ComponentPack:
        """
        生成标题层次结构
        """
        text_components = [co for co in cp.body if co.type == "text"]
        located = [co for co in text_components if co.location]
        if not located:
            return cp

        title_list = [co.title for co in located]
        title_bbox_list = [co.location[0] for co in located]
        image = self.media.crop_image(source_path, title_bbox_list)

        leveled_title: list[str] = []
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                raw = self.llm.generate_levels(title_list, image)
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

        for co, title in zip(located, leveled_title):
            co.title_level = self._get_title_level(title)

        return cp

class AsyncLevelGenerator:
    def __init__(self, llm_client: AsyncQwenLLMClient, image_provider: ImageProvider):
        self.llm = llm_client
        self.media = image_provider
    
    def _get_title_level(self, title: str) -> int:
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
        text_components = [co for co in cp.body if co.type == "text"]
        located = [co for co in text_components if co.location]
        if not located:
            return cp

        title_list = [co.title for co in located]
        title_bbox_list = [co.location[0] for co in located]
        image = self.media.crop_image(source_path, title_bbox_list)

        leveled_title: list[str] = []
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
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

        for co, title in zip(located, leveled_title):
            co.title_level = self._get_title_level(title)

        return cp