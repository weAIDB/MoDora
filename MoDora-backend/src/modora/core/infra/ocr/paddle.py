from typing import Any, Iterator
import logging
from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.domain.ocr import OCRBlock

logger = logging.getLogger(__name__)


class PPStructureClient(OCRClient):
    """OCR client based on PPStructureV3.

    Supports layout analysis, table recognition, and document dewarping.
    """

    def __init__(self, settings: Settings):
        from paddleocr import PPStructureV3

        device = (settings.ocr_device or "").strip() or "gpu:6"
        kwargs: dict[str, Any] = {
            "device": device,
            "lang": settings.ocr_lang or "en",
            "use_table_recognition": bool(settings.ocr_use_table_recognition),
            "use_doc_unwarping": bool(settings.ocr_use_doc_unwarping),
            "layout_unclip_ratio": settings.ocr_layout_unclip_ratio,
            "text_recognition_batch_size": settings.ocr_text_recognition_batch_size,
        }
        self._model = PPStructureV3(**kwargs)
        self.device = device
        self.lang = kwargs.get("lang")

    def _parse_response(self, res: Any, page_id: int) -> list[OCRBlock]:
        """Parse the response from PPStructureV3 into a list of OCRBlocks.

        Args:
            res: The response from the model.
            page_id: The ID of the page.

        Returns:
            list[OCRBlock]: A list of parsed OCR blocks.
        """
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
        """Iteratively predict OCR results for images or paths.

        Args:
            images_or_path: Images or a path to images to process.

        Yields:
            Iterator[list[OCRBlock]]: An iterator yielding a list of OCR blocks for each image.
        """
        for i, res in enumerate(self._model.predict_iter(images_or_path)):
            yield self._parse_response(res, page_id=i + 1)


class PaddleOCRVLClient(OCRClient):
    """OCR client based on the PaddleOCRVL-1.5 model.

    This model is more accurate but is currently very slow.
    """

    def __init__(self, settings: Settings, model_class_name: str = "PaddleOCRVL"):
        from paddleocr import PaddleOCRVL

        device = (settings.ocr_device or "").strip() or "gpu:6"
        kwargs: dict[str, Any] = {
            "device": device,
            "use_chart_recognition": bool(settings.ocr_use_table_recognition),
            "use_doc_unwarping": bool(settings.ocr_use_doc_unwarping),
            "layout_unclip_ratio": settings.ocr_layout_unclip_ratio,
            "text_recognition_batch_size": settings.ocr_text_recognition_batch_size,
        }
        self._model = PaddleOCRVL(**kwargs)
        self.device = device

    def _parse_response(self, res: Any, page_id: int) -> list[OCRBlock]:
        """Parse the response from PaddleOCRVL into a list of OCRBlocks.

        Args:
            res: The response from the model.
            page_id: The ID of the page.

        Returns:
            list[OCRBlock]: A list of parsed OCR blocks.
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
        """Iteratively predict OCR results for images or paths.

        Args:
            images_or_path: Images or a path to images to process.

        Yields:
            Iterator[list[OCRBlock]]: An iterator yielding a list of OCR blocks for each image.
        """
        for i, res in enumerate(self._model.predict_iter(images_or_path)):
            yield self._parse_response(res, page_id=i + 1)
