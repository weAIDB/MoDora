from __future__ import annotations

import logging
from modora.core.settings import Settings
from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.infra.llm.qwen import AsyncQwenLLMClient
from modora.core.infra.llm.remote import AsyncRemoteLLMClient


class AsyncLLMFactory:
    """
    Factory class for creating Async LLM Clients based on settings.
    """

    @staticmethod
    def create(settings: Settings | None = None, mode: str | None = None) -> BaseAsyncLLMClient:
        """
        Create and return an appropriate AsyncLLMClient instance.
        
        Args:
            settings: Settings object. If None, loads from default.
            mode: Explicit mode selection ("local" or "remote"). If None, auto-detects based on priority.

        Priority (when mode is None):
        1. Local Qwen (if llm_local_model is configured)
        2. Remote OpenAI-compatible (if api_key and api_base are configured)
        """
        settings = settings or Settings.load()

        if mode:
            mode = mode.lower().strip()
            if mode == "local":
                logging.getLogger(__name__).info("Forced mode 'local'. Using AsyncQwenLLMClient.")
                return AsyncQwenLLMClient(settings)
            elif mode == "remote":
                logging.getLogger(__name__).info("Forced mode 'remote'. Using AsyncRemoteLLMClient.")
                return AsyncRemoteLLMClient(settings)
            else:
                logging.getLogger(__name__).warning(f"Unknown mode '{mode}', falling back to auto-detect.")

        # Check for Local Qwen Configuration
        if settings.llm_local_model:
            logging.getLogger(__name__).info(f"Using AsyncQwenLLMClient with model: {settings.llm_local_model}")
            return AsyncQwenLLMClient(settings)

        if settings.api_key and settings.api_base:
            logging.getLogger(__name__).info("Using AsyncRemoteLLMClient with configured API settings")
            return AsyncRemoteLLMClient(settings)

        logging.getLogger(__name__).info("No explicit LLM configuration found in settings, defaulting to AsyncRemoteLLMClient (will attempt local.json fallback)")
        return AsyncRemoteLLMClient(settings)
