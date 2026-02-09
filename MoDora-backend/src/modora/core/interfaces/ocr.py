from abc import ABC, abstractmethod
from typing import Any, Iterator
from modora.core.domain.ocr import OCRBlock


class OCRClient(ABC):
    @abstractmethod
    def predict_iter(self, images_or_path: Any) -> Iterator[list[OCRBlock]]:
        """
        Run OCR prediction and return an iterator of results (one list of blocks per page/image).
        """
        pass
