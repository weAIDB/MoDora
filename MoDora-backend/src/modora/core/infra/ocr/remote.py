from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Iterator

import requests

from modora.core.settings import Settings
from modora.core.interfaces.ocr import OCRClient
from modora.core.domain.ocr import OCRBlock

logger = logging.getLogger(__name__)


class PaddleOCRRemoteClient(OCRClient):
    """OCR client based on the PaddleOCR cloud service (aistudio-app job API).

    Submits files as async jobs and polls for results, so no local GPU or
    PaddleOCR installation is required. The result JSONL is parsed into
    OCRBlocks compatible with the local PPStructureV3 client.
    """

    def __init__(self, settings: Settings):
        self.api_base = (settings.ocr_api_base or "").rstrip("/")
        self.api_key = settings.ocr_api_key
        self.model = settings.ocr_api_model or "PP-StructureV3"
        self.poll_interval_s = settings.ocr_api_poll_interval_s
        self.timeout_s = settings.ocr_api_timeout_s
        if not self.api_base or not self.api_key:
            raise ValueError(
                "ocr_api_base and ocr_api_key are required for remote OCR"
            )
        self.device = "remote"

    def _submit_job(self, file_bytes: bytes, filename: str) -> str:
        """Upload the file and return the job id."""
        headers = {"Authorization": f"bearer {self.api_key}"}
        data = {
            "model": self.model,
            "optionalPayload": json.dumps(
                {
                    "useDocOrientationClassify": False,
                    "useDocUnwarping": False,
                    "useChartRecognition": False,
                }
            ),
        }
        files = {"file": (filename, file_bytes)}
        resp = requests.post(
            self.api_base, headers=headers, data=data, files=files, timeout=300
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Remote OCR job submission failed ({resp.status_code}): {resp.text[:500]}"
            )
        return resp.json()["data"]["jobId"]

    def _wait_for_result(self, job_id: str) -> list[dict]:
        """Poll the job until done and return the parsed JSONL result lines."""
        headers = {"Authorization": f"bearer {self.api_key}"}
        deadline = time.monotonic() + self.timeout_s
        while time.monotonic() < deadline:
            resp = requests.get(f"{self.api_base}/{job_id}", headers=headers, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Remote OCR job polling failed ({resp.status_code}): {resp.text[:500]}"
                )
            data = resp.json().get("data", {})
            state = data.get("state")
            if state == "done":
                json_url = data["resultUrl"]["jsonUrl"]
                return self._download_result(json_url)
            if state == "failed":
                raise RuntimeError(f"Remote OCR job failed: {data.get('errorMsg')}")
            time.sleep(self.poll_interval_s)
        raise TimeoutError(
            f"Remote OCR job {job_id} did not finish within {self.timeout_s}s"
        )

    def _download_result(self, json_url: str) -> list[dict]:
        """Download the JSONL result and return one parsed line per page."""
        resp = requests.get(json_url, timeout=300)
        resp.raise_for_status()
        lines = []
        for line in resp.text.strip().splitlines():
            line = line.strip()
            if line:
                lines.append(json.loads(line))
        return lines

    def _parse_response(self, line: dict, page_id: int) -> list[OCRBlock]:
        """Parse one JSONL line into a list of OCRBlocks.

        Each line contains a "result" with "layoutParsingResults" (one entry
        per page). Bboxes are rescaled by 0.5 to align with the local
        PPStructureV3 coordinate convention.
        """
        blocks: list[OCRBlock] = []
        result = line.get("result", {})
        page_res_list = self._parsing_res_list(result)
        for block_id, item in enumerate(page_res_list):
            blocks.append(
                OCRBlock(
                    page_id=page_id,
                    block_id=block_id,
                    bbox=[0.5 * x for x in item["bbox"]],
                    label=item["label"],
                    content=item["content"],
                )
            )
        return blocks

    @staticmethod
    def _parsing_res_list(result: dict) -> list[dict]:
        """Extract a normalized parsing list from a cloud result.

        The cloud prunedResult uses block_label/block_content/block_bbox keys
        while the local PPStructureV3 uses label/content/bbox; both are
        normalized to the latter.
        """
        items: list[dict] = []
        for page in result.get("layoutParsingResults", []):
            pruned = page.get("prunedResult")
            if isinstance(pruned, str):
                try:
                    pruned = json.loads(pruned)
                except json.JSONDecodeError:
                    pruned = None
            if not isinstance(pruned, dict):
                continue
            for raw in pruned.get("parsing_res_list", []) or []:
                if not isinstance(raw, dict):
                    continue
                item = {
                    "bbox": raw.get("block_bbox") or raw.get("bbox") or [],
                    "label": raw.get("block_label") or raw.get("label") or "",
                    "content": raw.get("block_content") or raw.get("content") or "",
                }
                if item["bbox"]:
                    items.append(item)
        return items

    def predict_iter(self, images_or_path: Any) -> Iterator[list[OCRBlock]]:
        """Run OCR through the remote service.

        Args:
            images_or_path: A path to a PDF/image file, or raw image bytes.
                (ndarray inputs are not supported by the remote service.)

        Yields:
            Iterator[list[OCRBlock]]: One list of OCR blocks per page.
        """
        if isinstance(images_or_path, (bytes, bytearray)):
            file_bytes = bytes(images_or_path)
            filename = "upload.pdf"
        elif isinstance(images_or_path, str):
            with open(images_or_path, "rb") as f:
                file_bytes = f.read()
            filename = images_or_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        elif isinstance(images_or_path, Path):
            with open(images_or_path, "rb") as f:
                file_bytes = f.read()
            filename = images_or_path.name
        else:
            raise ValueError(
                "Remote OCR only supports file paths or bytes, got "
                f"{type(images_or_path)}"
            )

        logger.info(f"Submitting remote OCR job for {filename}")
        job_id = self._submit_job(file_bytes, filename)
        logger.info(f"Remote OCR job submitted, job id: {job_id}")

        lines = self._wait_for_result(job_id)
        # One JSONL line per uploaded page batch; page ids start from 1
        for page_id, line in enumerate(lines, start=1):
            yield self._parse_response(line, page_id=page_id)
