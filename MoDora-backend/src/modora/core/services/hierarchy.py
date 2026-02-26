from __future__ import annotations

import ast
import asyncio
import logging

from modora.core.domain.component import ComponentPack
from modora.core.settings import Settings
from modora.core.infra.llm.local import AsyncLocalLLMClient
from modora.core.interfaces.media import ImageProvider


class AsyncLevelGenerator:
    """Asynchronous hierarchy generator.

    Responsible for using LLM to correct or generate title hierarchies (Markdown style).
    """

    def __init__(self, llm_client: AsyncLocalLLMClient, image_provider: ImageProvider):
        self.llm = llm_client
        self.media = image_provider

    def _get_title_level(self, title: str) -> int:
        """Parses hierarchy depth from a title string with # (e.g., ### Title -> 3)."""
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
        """Uses LLM to generate or correct hierarchy information for text titles in the component pack.

        Args:
            source_path: Path to the PDF source file.
            cp: The component pack to process.
            config: System settings.
            logger: Logger instance.

        Returns:
            ComponentPack: Component pack with updated title_level.
        """
        text_components = [co for co in cp.body if co.type == "text"]
        located = [co for co in text_components if co.location]
        if not located:
            return cp

        # Prepare the list of titles to be processed and their corresponding location information
        title_list = [co.title for co in located]
        title_bbox_list = [co.location[0] for co in located]

        # Crop the title area image to assist the LLM in visual hierarchy judgment
        image = self.media.crop_image(source_path, title_bbox_list)

        leveled_title: list[str] = []
        max_attempts = 3
        # LLM call with retry mechanism
        for attempt in range(1, max_attempts + 1):
            try:
                # Invoke local multimodal LLM to generate titles with Markdown hierarchy
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

        # Fill the generated hierarchy information back into the components
        for co, title in zip(located, leveled_title):
            co.title_level = self._get_title_level(title)

        return cp
