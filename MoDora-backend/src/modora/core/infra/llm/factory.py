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
        settings: Settings | None = None, instance_id: str | None = None
    ) -> BaseAsyncLLMClient:
        """Creates and returns a suitable AsyncLLMClient instance.

        Args:
            settings: Configuration object. If None, the default configuration is loaded.
            instance_id: Optional specific model instance ID to use. If provided, it determines
                whether to use a local or remote client.

        Returns:
            A suitable AsyncLLMClient instance.
        """
        settings = settings or Settings.load()
        logger = logging.getLogger(__name__)

        # If instance_id is provided, resolve it and use its configuration
        if instance_id:
            instance = settings.resolve_model_instance(instance_id)
            if instance:
                if instance.type == "local":
                    return AsyncLocalLLMClient(settings, instance_id=instance_id)
                else:
                    return AsyncRemoteLLMClient(settings, instance_id=instance_id)
            else:
                logger.warning(f"Instance ID '{instance_id}' not found in settings.")

        # Auto-detection based on model_instances
        for inst_id, inst in settings.model_instances.items():
            if inst.type == "local" and inst.model:
                logger.info(f"Auto-detected local model instance: {inst_id}")
                return AsyncLocalLLMClient(settings, instance_id=inst_id)
        
        for inst_id, inst in settings.model_instances.items():
            if inst.type == "remote" and inst.base_url and inst.api_key:
                logger.info(f"Auto-detected remote model instance: {inst_id}")
                return AsyncRemoteLLMClient(settings, instance_id=inst_id)

        logger.info(
            "No explicit LLM configuration found, defaulting to AsyncRemoteLLMClient"
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
