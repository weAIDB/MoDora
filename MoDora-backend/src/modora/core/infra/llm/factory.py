from __future__ import annotations

import logging
from modora.core.settings import Settings
from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.infra.llm.embedding import AsyncEmbeddingClient
from modora.core.infra.llm.local import AsyncLocalLLMClient
from modora.core.infra.llm.remote import AsyncRemoteLLMClient
from modora.core.infra.llm.rerank import AsyncRerankClient


class AsyncLLMFactory:
    """Factory class for asynchronous LLM clients, creating corresponding client instances based on configuration."""

    @staticmethod
    def create(
        settings: Settings | None = None, mode: str | None = None
    ) -> BaseAsyncLLMClient:
        """Creates and returns a suitable AsyncLLMClient instance.

        Args:
            settings: Configuration object. If None, the default configuration is loaded.
            mode: Explicit mode selection ("local" or "remote"). If None, it is automatically
                detected based on priority.

        Returns:
            A suitable AsyncLLMClient instance.

        Priority logic (when mode is None):
            1. Local Qwen (if llm_local_model is configured).
            2. Remote OpenAI-compatible interface (if api_key and api_base are configured).
        """
        settings = settings or Settings.load()
        logger = logging.getLogger(__name__)

        if mode:
            mode = mode.lower().strip()
            if mode == "local":
                logger.info("Forced mode to 'local'. Using AsyncLocalLLMClient.")
                return AsyncLocalLLMClient(settings)
            elif mode == "remote":
                logger.info("Forced mode to 'remote'. Using AsyncRemoteLLMClient.")
                return AsyncRemoteLLMClient(settings)
            else:
                logger.warning(
                    f"Unknown mode '{mode}', falling back to auto-detection."
                )

        # Check local LLM configuration
        if settings.llm_local_model:
            logger.info(
                f"Using AsyncLocalLLMClient with model: {settings.llm_local_model}"
            )
            return AsyncLocalLLMClient(settings)

        # Check remote API configuration
        if settings.api_key and settings.api_base:
            logger.info("Using AsyncRemoteLLMClient with configured API settings")
            return AsyncRemoteLLMClient(settings)

        logger.info(
            "No explicit LLM configuration found in settings, defaulting to AsyncRemoteLLMClient (will attempt local.json fallback)"
        )
        return AsyncRemoteLLMClient(settings)

    @staticmethod
    def create_embedding(settings: Settings | None = None) -> AsyncEmbeddingClient:
        settings = settings or Settings.load()
        return AsyncEmbeddingClient(settings)

    @staticmethod
    def create_rerank(settings: Settings | None = None) -> AsyncRerankClient:
        settings = settings or Settings.load()
        return AsyncRerankClient(settings)
