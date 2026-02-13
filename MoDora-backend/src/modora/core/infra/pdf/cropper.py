from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import fitz
from PIL import Image

from modora.core.domain.component import Location
from modora.core.interfaces.media import ImageProvider

# If cropping fails (PDF cannot be opened / page number out of bounds / illegal bbox, etc.), return base64 of 1x1 blank PNG.
_BLANK_1X1_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAFh4kXcAAAAASUVORK5CYII="


def _normalize_pdf_path(pdf_path: str) -> str:
    """Compatible with source=file:/path/to.pdf format for fitz.open."""
    p = (pdf_path or "").strip()
    if p.startswith("file:"):
        p = p[len("file:") :]
    return p


def crop_pdf_image_task(pdf_path: str, bbox_data: list[dict]) -> str:
    """Independent task function to crop images from PDF.

    This function is designed to be picklable and can run in an independent process.

    Args:
        pdf_path: Path to the PDF file.
        bbox_data: List of dictionaries containing 'page' (1-based) and 'bbox' [x0, y0, x1, y1].

    Returns:
        Base64 encoded string of the merged image.
    """
    pdf_path = _normalize_pdf_path(pdf_path)
    try:
        pdf_document = fitz.open(pdf_path)
    except Exception:
        return _BLANK_1X1_PNG_BASE64

    images: list[Image.Image] = []
    try:
        for data in bbox_data:
            page_idx = data["page"] - 1
            crop_range = data["bbox"]
            if page_idx < 0 or page_idx >= len(pdf_document):
                continue

            page = pdf_document[page_idx]
            pix = page.get_pixmap(clip=crop_range)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    finally:
        pdf_document.close()

    if not images:
        return _BLANK_1X1_PNG_BASE64

    total_width = max(int(img.width) for img in images)
    total_height = sum(int(img.height) for img in images)
    merged_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for img in images:
        merged_image.paste(img, (0, y_offset))
        y_offset += int(img.height)

    # If image is too large (e.g., > 1024x1024), perform scaling
    # Limit maximum size to reduce token consumption
    MAX_SIZE = 1024
    if merged_image.width > MAX_SIZE or merged_image.height > MAX_SIZE:
        merged_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    buffered = io.BytesIO()
    merged_image.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.read()).decode("utf-8")


def bbox_to_base64(pdf_path: str, bbox_list: list[Location]) -> str:
    """Wrapper function for backward compatibility.

    Note: Calling this function directly runs in the current process/thread, which may not be safe for fitz.
    It is recommended to use crop_pdf_image_task with ProcessPoolExecutor in concurrent scenarios.
    """
    bbox_data = [{"page": loc.page, "bbox": loc.bbox} for loc in bbox_list]
    return crop_pdf_image_task(pdf_path, bbox_data)


def render_ocr_json_to_pdf(
    ocr_json_path: str, out_pdf_path: str | None = None, pdf_path: str | None = None
) -> str:
    """Renders bbox/label from OCR output JSON back to PDF pages and outputs the annotated PDF."""
    ocr_p = Path(ocr_json_path)
    obj = json.loads(ocr_p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("OCR JSON must be an object")

    if pdf_path is None:
        source = obj.get("source", "")
        if source.startswith("file:"):
            pdf_path = source[len("file:") :]
        else:
            raise ValueError(
                "pdf_path is not provided and source is not in file:<path> format"
            )

    if out_pdf_path is None:
        out_pdf_path = str(ocr_p.with_suffix("")) + ".rendered.pdf"

    blocks = obj.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("blocks must be a list")

    def color_for(label: str) -> tuple[float, float, float]:
        """Generate fixed colors for different labels."""
        palette = [
            (1.0, 0.0, 0.0),  # Red
            (0.0, 0.6, 0.0),  # Green
            (0.0, 0.3, 1.0),  # Blue
            (1.0, 0.5, 0.0),  # Orange
            (0.6, 0.0, 0.8),  # Purple
            (0.0, 0.7, 0.7),  # Cyan
        ]
        idx = abs(hash(label)) % len(palette)
        return palette[idx]

    doc = fitz.open(pdf_path)
    try:
        for b in blocks:
            if not isinstance(b, dict):
                continue
            page_id = b.get("page_id")
            bbox = b.get("bbox")
            label = b.get("label")
            block_id = b.get("block_id")

            if not isinstance(page_id, int):
                continue
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            if not isinstance(label, str):
                label = "unknown"

            page_idx = page_id - 1
            if page_idx < 0 or page_idx >= len(doc):
                continue

            try:
                rect = fitz.Rect(
                    float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                )
            except Exception:
                continue

            page = doc[page_idx]
            color = color_for(label)
            page.draw_rect(rect, color=color, width=1.0)

            text = f"{label}"
            if isinstance(block_id, int):
                text = f"{label}#{block_id}"

            x = rect.x0
            y = max(0.0, rect.y0 - 6.0)
            page.insert_text((x, y), text, fontsize=6.0, color=color)

        doc.save(out_pdf_path)
        return out_pdf_path
    finally:
        doc.close()


class PDFCropper(ImageProvider):
    """PDF image cropping adapter.

    Implements the ImageProvider interface, using PyMuPDF (fitz) to crop specified areas from PDF.
    """

    def crop_image(
        self,
        source_path: str | dict[str, str],
        locations: list[Location],
        file_names: list[str] | None = None,
    ) -> list[str]:
        """Crop images based on location information.

        Supports single or multiple documents. For multiple documents, locations should contain correct file_name.

        Args:
            source_path: PDF path or mapping from filename to path.
            locations: List of locations to crop.
            file_names: Optional list of filenames. If provided and file_name in locations is empty, the first one is used by default.

        Returns:
            List of cropped Base64 images.
        """
        if not locations:
            return []

        # Simple implementation: group cropping by file, then return base64 list
        results: list[str] = []

        # Simple implementation: Crop by file group and return base64 list
        # In actual multi-document RAG, we typically return a large combined image or multiple images
        # To maintain compatibility with the existing reason_retrieved interface, we return multiple cropped images
        results = []

        # Grouping
        grouped: dict[str, list[Location]] = {}
        for loc in locations:
            fn = loc.file_name
            if not fn and file_names:
                fn = file_names[0]
            if not fn and isinstance(source_path, str):
                fn = "default"

            if fn not in grouped:
                grouped[fn] = []
            grouped[fn].append(loc)

        for fn, locs in grouped.items():
            path = source_path
            if isinstance(source_path, dict):
                path = source_path.get(fn, "")
            if not path or not Path(str(path)).exists():
                continue

            # Use existing bbox_to_base64 (synchronous version, currently called synchronously by QAService)
            # Note: Can be optimized to asynchronous later
            img_b64 = bbox_to_base64(str(path), locs)
            results.append(img_b64)

        return results

    def pdf_to_base64(self, source: str) -> str:
        """Converts the entire PDF (all pages) into a single vertically stacked Base64 image.

        Args:
            source: Path to the PDF file.

        Returns:
            Base64 encoded string of the combined image.
        """
        source = _normalize_pdf_path(source)
        try:
            doc = fitz.open(source)
        except Exception:
            return _BLANK_1X1_PNG_BASE64

        # Create full-page bboxes for each page
        bbox_data = []
        for i, page in enumerate(doc):
            rect = page.rect
            bbox_data.append(
                {"page": i + 1, "bbox": [rect.x0, rect.y0, rect.x1, rect.y1]}
            )
        doc.close()

        return crop_pdf_image_task(source, bbox_data)
