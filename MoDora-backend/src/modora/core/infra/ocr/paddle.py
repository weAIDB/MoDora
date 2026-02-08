from typing import Any, Iterator
import logging
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.domain.ocr import OCRBlock

logger = logging.getLogger(__name__)

class PPStructureClient(OCRClient):
    def __init__(self, settings: Settings):
        from paddleocr import PPStructureV3
        device = (settings.ocr_device or "").strip() or "gpu:6"
        kwargs: dict[str, Any] = {
            "device": device,
            "lang": settings.ocr_lang or "en",
            "use_table_recognition": bool(settings.ocr_use_table_recognition),
            "use_doc_unwarping": bool(settings.ocr_use_doc_unwarping),
            "layout_unclip_ratio": settings.ocr_layout_unclip_ratio,
        }
        self._model = PPStructureV3(**kwargs)
        self.device = device
        self.lang = kwargs.get("lang")

    def _parse_response(self, res: Any, page_id: int) -> list[OCRBlock]:
        """Parse PPStructureV3 response into OCRBlocks."""
        res_list = res["parsing_res_list"]

        blocks: list[OCRBlock] = []
        for item in res_list:
            bbox = [0.5 * x for x in item.bbox]
            blocks.append(
                OCRBlock(
                    page_id=page_id,
                    block_id=item.index,
                    bbox=bbox,
                    label=item.label,
                    content=item.content,
                )
            )
        return blocks

    def predict_iter(self, images_or_path: Any) -> Iterator[list[OCRBlock]]:
        for i, res in enumerate(self._model.predict_iter(images_or_path)):
            yield self._parse_response(res, page_id=i + 1)

class PaddleOCRVLClient(OCRClient):
    def __init__(self, settings: Settings, model_class_name: str = "PaddleOCRVL"):
        from paddleocr import PaddleOCRVL
        device = (settings.ocr_device or "").strip() or "gpu:6"
        kwargs: dict[str, Any] = {
            "device": device,
            "use_chart_recognition": bool(settings.ocr_use_table_recognition),
            "use_doc_unwarping": bool(settings.ocr_use_doc_unwarping),
            "layout_unclip_ratio": settings.ocr_layout_unclip_ratio,
        }
        self._model = PaddleOCRVL(**kwargs)
        self.device = device

    def _parse_response(self, res: Any, page_id: int) -> list[OCRBlock]:
        """
        Parse PaddleOCRVL response into OCRBlocks.
        TODO: Implement specific parsing logic for PaddleOCRVL.
        """
        res_list = res["parsing_res_list"]

        blocks: list[OCRBlock] = []
        for i, item in enumerate(res_list):
            bbox = [0.5 * x for x in item.bbox]
            blocks.append(
                OCRBlock(
                    page_id=page_id,
                    block_id=i,
                    bbox=bbox,
                    label=item.label,
                    content=item.content,
                )
            )
        return blocks
            
        
    
    def predict_iter(self, images_or_path: Any) -> Iterator[list[OCRBlock]]:
        for i, res in enumerate(self._model.predict_iter(images_or_path)):
            yield self._parse_response(res, page_id=i + 1)
