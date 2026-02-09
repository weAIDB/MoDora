from __future__ import annotations

import logging
from modora.core.settings import Settings
from modora.core.infra.llm.base import BaseAsyncLLMClient
from modora.core.infra.llm.local import AsyncLocalLLMClient
from modora.core.infra.llm.remote import AsyncRemoteLLMClient


class AsyncLLMFactory:
    """
    异步 LLM 客户端工厂类，根据配置创建对应的客户端实例。
    """

    @staticmethod
    def create(
        settings: Settings | None = None, mode: str | None = None
    ) -> BaseAsyncLLMClient:
        """
        创建并返回合适的 AsyncLLMClient 实例。

        Args:
            settings: 配置对象。如果为 None，则加载默认配置。
            mode: 显式模式选择（"local" 或 "remote"）。如果为 None，则根据优先级自动检测。

        优先级逻辑（当 mode 为 None 时）：
        1. 本地 Qwen (如果配置了 llm_local_model)
        2. 远程 OpenAI 兼容接口 (如果配置了 api_key 和 api_base)
        """
        settings = settings or Settings.load()
        logger = logging.getLogger(__name__)

        if mode:
            mode = mode.lower().strip()
            if mode == "local":
                logger.info("强制模式为 'local'。使用 AsyncLocalLLMClient。")
                return AsyncLocalLLMClient(settings)
            elif mode == "remote":
                logger.info("强制模式为 'remote'。使用 AsyncRemoteLLMClient。")
                return AsyncRemoteLLMClient(settings)
            else:
                logger.warning(f"未知模式 '{mode}'，回退到自动检测。")

        # 检查本地 LLM 配置
        if settings.llm_local_model:
            logger.info(f"使用 AsyncLocalLLMClient，模型为: {settings.llm_local_model}")
            return AsyncLocalLLMClient(settings)

        # 检查远程 API 配置
        if settings.api_key and settings.api_base:
            logger.info("使用已配置 API 设置的 AsyncRemoteLLMClient")
            return AsyncRemoteLLMClient(settings)

        logger.info(
            "设置中未发现明确的 LLM 配置，默认使用 AsyncRemoteLLMClient（将尝试 local.json 回退）"
        )
        return AsyncRemoteLLMClient(settings)
