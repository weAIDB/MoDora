import asyncio

from modora.core.domain import TITLE, ComponentPack
from modora.core.interfaces.llm import AsyncLLMClient
from modora.core.interfaces.media import ImageProvider


class EnrichmentService:
    """
    信息增强服务。
    负责协调图片提供者和 LLM 客户端，对文档中的非文本组件（图片、图表、表格）进行信息增强（生成标题、元数据和内容描述）。
    """

    def __init__(
        self,
        llm_client: AsyncLLMClient,
        image_provider: ImageProvider,
        max_workers: int = 4,
    ):
        """
        初始化信息增强服务。

        Args:
            llm_client: LLM 客户端实例，用于生成文本标注
            image_provider: 图片提供者实例，用于获取组件截图
            max_workers: 并发处理的最大线程数
        """
        self.llm = llm_client
        self.media = image_provider
        self.max_workers = max_workers

    async def enrich_async(self, co_pack: ComponentPack, source: str) -> ComponentPack:
        """
        异步执行增强流程。
        """
        tasks = []
        for co in co_pack.body:
            if co.type in ["image", "chart", "table"]:
                tasks.append(co)

        if not tasks:
            return co_pack

        async def _process_one(co):
            try:
                # 获取组件截图（IO 操作，跑在线程池）
                loop = asyncio.get_running_loop()
                base64_img = await loop.run_in_executor(
                    None, self.media.crop_image, source, co
                )
                # 调用 LLM 生成标注（异步）
                title, metadata, data = await self.llm.generate_annotation_async(
                    base64_img, co.type
                )
                return co, title, metadata, data
            except Exception:
                return None

        # 使用 asyncio.gather 并发处理
        sem = asyncio.Semaphore(self.max_workers)

        async def _sem_process(co):
            async with sem:
                return await _process_one(co)

        results = await asyncio.gather(*[_sem_process(co) for co in tasks])

        for result in results:
            if result:
                co, title, metadata, data = result
                co.title = title if co.title == TITLE else co.title
                co.metadata = metadata
                co.data = data if co.data == "" else co.data

        return co_pack
