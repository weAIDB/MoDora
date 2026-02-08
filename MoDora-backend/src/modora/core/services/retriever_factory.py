from __future__ import annotations

import logging
from typing import Literal

from modora.core.infra.llm.factory import AsyncLLMFactory
from modora.core.infra.pdf.cropper import PDFCropper
from modora.core.services.retriever import AsyncRetriever
from modora.core.services.fast_retriever import FastLocationAsyncRetriever
from modora.core.settings import Settings


class RetrieverFactory:
    """
    Factory for creating retrievers based on strategy.
    """

    @staticmethod
    def create(
        settings: Settings,
        logger: logging.Logger,
        strategy: Literal["semantic", "fast_location"] = "fast_location",
    ) -> AsyncRetriever:
        """
        Create a retriever instance.

        Args:
            settings: Application settings.
            logger: Logger instance.
            strategy: Retrieval strategy.
                - "semantic": Pure semantic retrieval (AsyncRetriever).
                - "fast_location": Location-optimized retrieval (FastLocationAsyncRetriever).
                  Falls back to semantic if no location constraints.

        Returns:
            An instance of AsyncRetriever (or subclass).
        """
        llm_client = AsyncLLMFactory.create(settings, mode="local")
        cropper = PDFCropper()

        if strategy == "fast_location":
            return FastLocationAsyncRetriever(llm_client, cropper, logger)
        elif strategy == "semantic":
            return AsyncRetriever(llm_client, cropper, logger)
        else:
            raise ValueError(f"Unknown retriever strategy: {strategy}")
