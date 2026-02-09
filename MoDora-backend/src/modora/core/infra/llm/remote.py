from __future__ import annotations

import logging
from openai import AsyncOpenAI
from modora.core.settings import Settings
from modora.core.infra.llm.base import BaseAsyncLLMClient


class AsyncRemoteLLMClient(BaseAsyncLLMClient):
    """
    异步远程 LLM 客户端，继承自 BaseAsyncLLMClient。
    专门用于调用远程 OpenAI 兼容接口（如 Gemini, GPT 等）。
    """

    def __init__(self, settings: Settings | None = None):
        """
        初始化远程客户端。

        Args:
            settings: 配置对象，如果为 None 则加载默认配置。
        """
        super().__init__(settings)
        self._init_client()

    def _init_client(self):
        """
        根据配置初始化 OpenAI 异步客户端实例。
        从 settings 中读取 api_key, api_base 和 api_model。
        """
        self.api_key = getattr(self.settings, "api_key", None)
        self.base_url = getattr(self.settings, "api_base", None)
        self.model = getattr(self.settings, "api_model", "gemini-2.5-flash")

        if self.api_key and self.base_url:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        else:
            self.client = None

    async def _call_llm(
        self, prompt: str, base64_image: str | list[str] | None = None
    ) -> str:
        """
        实现抽象方法以调用远程 LLM 接口。
        支持发送文本 Prompt 和多张 Base64 编码的图片。

        Args:
            prompt: 提示词文本。
            base64_image: 单个或多个图片的 Base64 编码字符串。

        Returns:
            str: 模型生成的文本响应内容。
        """
        if not self.client:
            logging.getLogger(__name__).error(
                "远程 LLM 客户端未初始化（缺少 api_key 或 api_base）"
            )
            return ""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        if base64_image:
            if isinstance(base64_image, str):
                base64_image = [base64_image]

            for img in base64_image:
                messages[0]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                    }
                )

        try:
            # 调用 OpenAI 兼容接口的 Chat Completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=16384,  # 增加 token 限制以支持长文本生成
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logging.getLogger(__name__).error(f"远程 LLM 调用失败: {e}")
            return ""
