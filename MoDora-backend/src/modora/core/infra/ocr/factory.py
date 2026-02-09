from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.paddle import PPStructureClient, PaddleOCRVLClient


class OCRFactory:
    """
    用于创建 OCR 客户端的工厂类。
    """

    @staticmethod
    def create(settings: Settings) -> OCRClient:
        """
        根据指定的模型类型创建 OCR 客户端实例。

        模型类型 (settings.ocr_model):
            "ppstructure" -> PPStructureV3 (默认)
            "paddle_ocr_vl" -> PaddleOCRVL (可选)
        """
        model = settings.ocr_model or "ppstructure"
        if model == "ppstructure":
            return PPStructureClient(settings)
        elif model == "paddle_ocr_vl":
            return PaddleOCRVLClient(settings)
        else:
            raise ValueError(f"未知 OCR 模型类型: {model}")
