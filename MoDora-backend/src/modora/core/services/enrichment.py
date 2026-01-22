import concurrent.futures

from modora.core.domain.component import TITLE, ComponentPack
from modora.core.interfaces.llm import LLMClient
from modora.core.interfaces.media import ImageProvider


class EnrichmentService:
    """
    信息增强服务。
    负责协调图片提供者和 LLM 客户端，对文档中的非文本组件（图片、图表、表格）进行信息增强（生成标题、元数据和内容描述）。
    """

    def __init__(
        self, llm_client: LLMClient, image_provider: ImageProvider, max_workers: int = 4
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

    def enrich(self, co_pack: ComponentPack, source: str) -> ComponentPack:
        """
        执行增强流程。
        遍历组件包，对支持的类型调用 LLM 生成描述信息。

        Args:
            co_pack: 待处理的组件包
            source: 源文件路径（用于截图）

        Returns:
            ComponentPack: 增强后的组件包
        """
        # 筛选需要增强的组件
        tasks = []
        for co in co_pack.body:
            if co.type in ["image", "chart", "table"]:
                tasks.append(co)

        if not tasks:
            return co_pack

        def _process_one(co):
            try:
                # 获取组件截图
                base64_img = self.media.crop_image(source, co)
                # 调用 LLM 生成标注
                title, metadata, data = self.llm.generate_annotation(
                    base64_img, co.type
                )
                return co, title, metadata, data
            except Exception:
                # 记录错误但不中断整体流程，返回 None
                return None

        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = [executor.submit(_process_one, co) for co in tasks]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    co, title, metadata, data = result
                    # 更新组件信息 (保留原有非默认标题)
                    co.title = title if co.title == TITLE else co.title
                    co.metadata = metadata
                    co.data = data if co.data == "" else co.data

        return co_pack
