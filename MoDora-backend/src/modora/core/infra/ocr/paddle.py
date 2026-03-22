from __future__ import annotations

from typing import Any, Iterator
import logging
import json
import os
import time

import requests

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

        device = (settings.ocr_device or "").strip() or "gpu:7"
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

        device = (settings.ocr_device or "").strip() or "gpu:7"
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


class PaddleOCRAPIClient(OCRClient):
    """OCR client backed by the Paddle OCR cloud jobs API."""

    def __init__(self, settings: Settings):
        self.job_url = (
            (settings.ocr_api_url or "").strip()
            or "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
        )
        self.token = (settings.ocr_api_token or "").strip()
        self.model = (settings.ocr_api_model or "").strip() or "PP-StructureV3"
        self.poll_interval_s = max(float(settings.ocr_api_poll_interval_s or 5.0), 1.0)
        self.optional_payload = {
            "useDocOrientationClassify": False,
            "useDocUnwarping": bool(settings.ocr_use_doc_unwarping),
            "useChartRecognition": bool(settings.ocr_use_table_recognition),
        }
        if not self.token:
            raise ValueError("ocr_api_token is required when ocr_model is 'paddle_api'")

    def predict_iter(self, images_or_path: Any) -> Iterator[list[OCRBlock]]:
        file_path = str(images_or_path)
        page_results = self._run_job(file_path)
        fallback_page_id = 1
        for parsed_page_id, page_result in page_results:
            page_id = parsed_page_id if parsed_page_id is not None else fallback_page_id
            yield self._parse_page(page_result, page_id=page_id)
            fallback_page_id = max(fallback_page_id, page_id + 1)

    def _run_job(self, file_path: str) -> list[tuple[int | None, dict[str, Any]]]:
        headers = {
            "Authorization": f"bearer {self.token}",
        }
        logger.info(
            "Submitting Paddle OCR API job",
            extra={"job_url": self.job_url, "ocr_model": self.model},
        )

        if str(file_path).startswith("http://") or str(file_path).startswith("https://"):
            headers["Content-Type"] = "application/json"
            payload = {
                "fileUrl": file_path,
                "model": self.model,
                "optionalPayload": self.optional_payload,
            }
            job_response = requests.post(self.job_url, json=payload, headers=headers, timeout=60)
        else:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"OCR input not found: {file_path}")
            data = {
                "model": self.model,
                "optionalPayload": json.dumps(self.optional_payload),
            }
            with open(file_path, "rb") as f:
                files = {"file": f}
                job_response = requests.post(
                    self.job_url,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=120,
                )

        job_response.raise_for_status()
        job_id = (((job_response.json() or {}).get("data") or {}).get("jobId") or "").strip()
        if not job_id:
            raise ValueError(f"Missing jobId in Paddle OCR response: {job_response.text[:500]}")

        logger.info("Paddle OCR API job submitted", extra={"job_id": job_id})
        json_url = self._poll_job(job_id=job_id, headers=headers)
        jsonl_response = requests.get(json_url, timeout=120)
        jsonl_response.raise_for_status()
        return self._parse_jsonl_payload(jsonl_response.text)

    def _poll_job(self, job_id: str, headers: dict[str, str]) -> str:
        while True:
            response = requests.get(f"{self.job_url}/{job_id}", headers=headers, timeout=60)
            response.raise_for_status()
            payload = (response.json() or {}).get("data") or {}
            state = str(payload.get("state") or "").strip().lower()
            if state == "done":
                result_url = payload.get("resultUrl") or {}
                json_url = result_url.get("jsonUrl") or result_url.get("jsonlUrl") or result_url.get("json_url")
                if not json_url:
                    raise ValueError(f"Paddle OCR job completed without jsonUrl: {payload}")
                logger.info("Paddle OCR API job completed", extra={"job_id": job_id})
                return str(json_url)
            if state == "failed":
                error_msg = payload.get("errorMsg") or payload.get("message") or "unknown error"
                raise RuntimeError(f"Paddle OCR job failed: {error_msg}")

            progress = payload.get("extractProgress") or {}
            logger.info(
                "Paddle OCR API job polling",
                extra={
                    "job_id": job_id,
                    "state": state or "unknown",
                    "extracted_pages": progress.get("extractedPages"),
                    "total_pages": progress.get("totalPages"),
                },
            )
            time.sleep(self.poll_interval_s)

    def _parse_jsonl_payload(self, body: str) -> list[tuple[int | None, dict[str, Any]]]:
        pages: list[tuple[int | None, dict[str, Any]]] = []
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            result = item.get("result")
            if isinstance(result, dict):
                pages.extend(self._collect_page_results(item, result))
            elif isinstance(result, list):
                for entry in result:
                    if isinstance(entry, dict):
                        pages.extend(self._collect_page_results(item, entry))
        if not pages:
            raise ValueError("Paddle OCR API returned empty JSONL payload")
        return pages

    def _collect_page_results(
        self, container: dict[str, Any], result: dict[str, Any]
    ) -> list[tuple[int | None, dict[str, Any]]]:
        layout_pages = result.get("layoutParsingResults")
        if isinstance(layout_pages, list) and layout_pages:
            collected: list[tuple[int | None, dict[str, Any]]] = []
            for page_index, entry in enumerate(layout_pages, start=1):
                if isinstance(entry, dict):
                    collected.append((page_index, entry))
            if collected:
                return collected

        nested_pages = result.get("pages")
        if isinstance(nested_pages, list) and nested_pages:
            collected: list[tuple[int | None, dict[str, Any]]] = []
            for entry in nested_pages:
                if not isinstance(entry, dict):
                    continue
                page_id = self._extract_page_id(entry)
                collected.append((page_id, entry))
            if collected:
                return collected

        page_id = self._extract_page_id(result)
        if page_id is None:
            page_id = self._extract_page_id(container)
        return [(page_id, result)]

    def _extract_page_id(self, node: Any) -> int | None:
        if isinstance(node, dict):
            direct_keys = (
                "page_id",
                "pageId",
                "page_no",
                "pageNo",
                "page_num",
                "pageNum",
                "page_number",
                "pageNumber",
                "page",
            )
            zero_based_keys = ("page_index", "pageIndex", "page_idx", "pageIdx")

            for key in direct_keys:
                value = node.get(key)
                page_id = self._coerce_page_id(value, zero_based=False)
                if page_id is not None:
                    return page_id

            for key in zero_based_keys:
                value = node.get(key)
                page_id = self._coerce_page_id(value, zero_based=True)
                if page_id is not None:
                    return page_id

            for value in node.values():
                page_id = self._extract_page_id(value)
                if page_id is not None:
                    return page_id

        elif isinstance(node, list):
            for item in node:
                page_id = self._extract_page_id(item)
                if page_id is not None:
                    return page_id

        return None

    @staticmethod
    def _coerce_page_id(value: Any, *, zero_based: bool) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            if not value.isdigit():
                return None
            numeric = int(value)
        elif isinstance(value, (int, float)):
            numeric = int(value)
        else:
            return None

        if zero_based:
            numeric += 1
        return numeric if numeric >= 1 else None

    def _parse_page(self, page_result: dict[str, Any], page_id: int) -> list[OCRBlock]:
        layout_results = page_result.get("layoutParsingResults")
        if not isinstance(layout_results, list):
            if any(key in page_result for key in ("prunedResult", "markdown", "inputImage")):
                layout_results = [page_result]
        if isinstance(layout_results, list) and layout_results:
            blocks = self._blocks_from_pruned_results(layout_results, page_id=page_id)
            if blocks:
                return blocks
            blocks = self._blocks_from_layout_results(layout_results, page_id=page_id)
            if blocks:
                return blocks

        markdown_text = self._extract_markdown_text(page_result)
        if markdown_text:
            logger.warning(
                "Paddle OCR API page missing structured blocks; using markdown fallback",
                extra={"page_id": page_id},
            )
            return [
                OCRBlock(
                    page_id=page_id,
                    block_id=0,
                    bbox=[0.0, 0.0, 1000.0, 1000.0],
                    label="text",
                    content=markdown_text,
                )
            ]
        return []

    def _blocks_from_pruned_results(
        self, layout_results: list[Any], page_id: int
    ) -> list[OCRBlock]:
        blocks: list[OCRBlock] = []
        block_id = 0
        for entry in layout_results:
            if not isinstance(entry, dict):
                continue
            pruned = entry.get("prunedResult")
            if not isinstance(pruned, dict):
                continue
            parsing_res_list = pruned.get("parsing_res_list")
            if not isinstance(parsing_res_list, list):
                continue
            for item in parsing_res_list:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("block_content") or "").strip()
                bbox_raw = item.get("block_bbox")
                if not text or not isinstance(bbox_raw, list) or len(bbox_raw) != 4:
                    continue
                bbox = [0.5 * float(v) for v in bbox_raw]
                raw_block_id = item.get("block_id")
                normalized_block_id = (
                    int(raw_block_id) if isinstance(raw_block_id, int) else block_id
                )
                blocks.append(
                    OCRBlock(
                        page_id=page_id,
                        block_id=normalized_block_id,
                        bbox=bbox,
                        label=self._normalize_label(
                            {"label": item.get("block_label") or "text"}
                        ),
                        content=text,
                    )
                )
                block_id += 1
        return blocks

    def _blocks_from_layout_results(
        self, layout_results: list[Any], page_id: int
    ) -> list[OCRBlock]:
        blocks: list[OCRBlock] = []
        block_id = 0
        for entry in layout_results:
            for item in self._iter_candidate_items(entry):
                text = self._extract_text(item)
                bbox = self._extract_bbox(item)
                if not text or bbox is None:
                    continue
                blocks.append(
                    OCRBlock(
                        page_id=page_id,
                        block_id=block_id,
                        bbox=bbox,
                        label=self._normalize_label(item),
                        content=text,
                    )
                )
                block_id += 1
        return blocks

    def _iter_candidate_items(self, node: Any) -> Iterator[dict[str, Any]]:
        if isinstance(node, dict):
            if self._extract_text(node) and self._extract_bbox(node) is not None:
                yield node
            for value in node.values():
                yield from self._iter_candidate_items(value)
        elif isinstance(node, list):
            for item in node:
                yield from self._iter_candidate_items(item)

    def _extract_markdown_text(self, node: Any) -> str:
        if isinstance(node, dict):
            markdown = node.get("markdown")
            if isinstance(markdown, dict):
                text = markdown.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
            for value in node.values():
                text = self._extract_markdown_text(value)
                if text:
                    return text
        elif isinstance(node, list):
            for item in node:
                text = self._extract_markdown_text(item)
                if text:
                    return text
        return ""

    def _extract_text(self, item: dict[str, Any]) -> str:
        for key in ("text", "content", "value", "textContent", "markdownText"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        markdown = item.get("markdown")
        if isinstance(markdown, dict):
            text = markdown.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
        return ""

    def _extract_bbox(self, item: dict[str, Any]) -> list[float] | None:
        for key in ("bbox", "box", "boundingBox", "region", "coordinate", "coordinates"):
            bbox = self._normalize_bbox_value(item.get(key))
            if bbox is not None:
                return bbox
        for key in ("poly", "polygon", "points"):
            bbox = self._normalize_bbox_value(item.get(key))
            if bbox is not None:
                return bbox
        return None

    def _normalize_bbox_value(self, value: Any) -> list[float] | None:
        if isinstance(value, dict):
            xs = []
            ys = []
            for x_key in ("x", "x0", "left"):
                if x_key in value:
                    xs.append(float(value[x_key]))
            for x_key in ("x1", "right"):
                if x_key in value:
                    xs.append(float(value[x_key]))
            for y_key in ("y", "y0", "top"):
                if y_key in value:
                    ys.append(float(value[y_key]))
            for y_key in ("y1", "bottom"):
                if y_key in value:
                    ys.append(float(value[y_key]))
            if len(xs) >= 2 and len(ys) >= 2:
                return [min(xs), min(ys), max(xs), max(ys)]
            return None

        if not isinstance(value, (list, tuple)) or not value:
            return None

        if len(value) == 4 and all(isinstance(v, (int, float)) for v in value):
            x0, y0, x1, y1 = value
            return [float(x0), float(y0), float(x1), float(y1)]

        points: list[tuple[float, float]] = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                points.append((float(item[0]), float(item[1])))
            elif isinstance(item, dict):
                x = item.get("x", item.get("left"))
                y = item.get("y", item.get("top"))
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    points.append((float(x), float(y)))
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return [min(xs), min(ys), max(xs), max(ys)]
        return None

    def _normalize_label(self, item: dict[str, Any]) -> str:
        raw = (
            item.get("label")
            or item.get("type")
            or item.get("blockType")
            or item.get("layoutType")
            or item.get("category")
            or "text"
        )
        value = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        mapping = {
            "doc_title": "doc_title",
            "title": "title",
            "paragraph_title": "paragraph_title",
            "figure_title": "figure_title",
            "vision_footnote": "vision_footnote",
            "table": "table",
            "chart": "chart",
            "image": "image",
            "figure": "image",
            "header": "header",
            "footer": "footer",
            "number": "number",
            "aside_text": "aside_text",
            "text": "text",
            "paragraph": "text",
        }
        return mapping.get(value, "text")
