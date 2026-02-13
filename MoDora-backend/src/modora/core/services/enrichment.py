import asyncio

from modora.core.domain import TITLE, ComponentPack
from modora.core.interfaces.llm import AsyncLLMClient
from modora.core.interfaces.media import ImageProvider


class EnrichmentService:
    """Information enrichment service.

    Responsible for coordinating image providers and LLM clients to perform information enrichment
    (generating titles, metadata, and content descriptions) for non-text components (images, charts, tables) in documents.
    """

    def __init__(
        self,
        llm_client: AsyncLLMClient,
        image_provider: ImageProvider,
        max_workers: int = 4,
    ):
        """Initializes the information enrichment service.

        Args:
            llm_client: LLM client instance for generating text annotations.
            image_provider: Image provider instance for obtaining component screenshots.
            max_workers: Maximum number of workers for concurrent processing.
        """
        self.llm = llm_client
        self.media = image_provider
        self.max_workers = max_workers

    async def enrich_async(self, co_pack: ComponentPack, source: str) -> ComponentPack:
        """Asynchronously executes the enrichment process.

        Args:
            co_pack: The component pack to enrich.
            source: The source document path or identifier.

        Returns:
            ComponentPack: The enriched component pack.
        """
        tasks = []
        for co in co_pack.body:
            if co.type in ["image", "chart", "table"]:
                tasks.append(co)

        if not tasks:
            return co_pack

        async def _process_one(co):
            try:
                # Capture component screenshot (IO operation, runs in thread pool)
                loop = asyncio.get_running_loop()
                base64_img = await loop.run_in_executor(
                    None, self.media.crop_image, source, co
                )
                # Invoke LLM to generate annotations (Asynchronous)
                title, metadata, data = await self.llm.generate_annotation_async(
                    base64_img, co.type
                )
                return co, title, metadata, data
            except Exception:
                return None

        # Use asyncio.gather for concurrent processing
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
