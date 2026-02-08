from typing import Optional
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.infra.ocr.paddle import PPStructureClient, PaddleOCRVLClient

class OCRFactory:
    """
    Factory for creating OCR clients.
    """
    
    @staticmethod
    def create(settings: Settings) -> OCRClient:
        """
        Create an OCR client instance based on the specified model type.
        
        Args:
            settings: Application settings.
            model_type: The type of OCR model to use.
                        "ppstructure" -> PPStructureV3 (Default)
                        "paddle_ocr_vl" -> PaddleOCRVL (Vision Language)
            
        Returns:
            An instance of OCRClient.
            
        Raises:
            ValueError: If the model_type is unknown.
        """
        model = settings.ocr_model or "ppstructure"
        if model == "ppstructure":
            return PPStructureClient(settings)
        elif model == "paddle_ocr_vl":
            return PaddleOCRVLClient(settings)
        else:
            raise ValueError(f"Unknown OCR model type: {model}")
