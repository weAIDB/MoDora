from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.paddle import (
    PPStructureClient,
    PaddleOCRAPIClient,
    PaddleOCRVLClient,
)


class OCRFactory:
    """Factory class for creating OCR clients."""

    @staticmethod
    def create(settings: Settings) -> OCRClient:
        """Create an OCR client instance based on the specified model type.

        Args:
            settings: The settings object containing the ocr_model type.
                Supported model types (settings.ocr_model):
                - "ppstructure" -> PPStructureV3 (default)
                - "paddle_ocr_vl" -> PaddleOCRVL (optional)
                - "paddle_api" -> Paddle OCR cloud API (PP-StructureV3)

        Returns:
            OCRClient: An instance of the OCR client.
        """
        model = settings.ocr_model or "ppstructure"
        if model == "ppstructure":
            return PPStructureClient(settings)
        elif model == "paddle_ocr_vl":
            return PaddleOCRVLClient(settings)
        elif model == "paddle_api":
            return PaddleOCRAPIClient(settings)
        else:
            raise ValueError(f"Unknown OCR model type: {model}")
