from __future__ import annotations

import base64
import io
import json
import sqlite3
from pathlib import Path

import fitz
from PIL import Image

from modora.core.domain.component import Location
from modora.core.interfaces.media import ImageProvider
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths

# If cropping fails (PDF cannot be opened / page number out of bounds / illegal bbox, etc.), return base64 of 1x1 blank PNG.
_BLANK_1X1_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAFh4kXcAAAAASUVORK5CYII="


def _normalize_pdf_path(pdf_path: str) -> str:
    """Compatible with source=file:/path/to.pdf format for fitz.open."""
    p = (pdf_path or "").strip()
    if p.startswith("file:"):
        p = p[len("file:") :]
    return p


def _image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.read()).decode("utf-8")


def _base64_to_image(data: str) -> Image.Image | None:
    try:
        raw = base64.b64decode(data)
        img = Image.open(io.BytesIO(raw))
        return img.convert("RGB")
    except Exception:
        return None


def _merge_images_to_base64(images: list[Image.Image | None]) -> str:
    valid = [img for img in images if img is not None]
    if not valid:
        return _BLANK_1X1_PNG_BASE64

    total_width = max(int(img.width) for img in valid)
    total_height = sum(int(img.height) for img in valid)
    merged_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for img in valid:
        merged_image.paste(img, (0, y_offset))
        y_offset += int(img.height)

    MAX_SIZE = 1024
    if merged_image.width > MAX_SIZE or merged_image.height > MAX_SIZE:
        merged_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    return _image_to_base64(merged_image)


def _crop_bboxes_to_images(
    pdf_path: str, bbox_data: list[dict]
) -> list[Image.Image | None]:
    pdf_path = _normalize_pdf_path(pdf_path)
    try:
        pdf_document = fitz.open(pdf_path)
    except Exception:
        return [None for _ in bbox_data]

    images: list[Image.Image | None] = []
    try:
        for data in bbox_data:
            page_idx = data["page"] - 1
            crop_range = data["bbox"]
            if page_idx < 0 or page_idx >= len(pdf_document):
                images.append(None)
                continue
            try:
                page = pdf_document[page_idx]
                
                # Ensure crop_range is within page bounds to avoid SystemError
                # crop_range is [x0, y0, x1, y1]
                rect = fitz.Rect(crop_range)
                # Intersect with page rect to ensure it's valid
                # if rect is completely outside, intersection is empty or invalid
                safe_rect = rect & page.rect
                
                if safe_rect.is_empty or safe_rect.width <= 0 or safe_rect.height <= 0:
                    images.append(None)
                    continue

                pix = page.get_pixmap(clip=safe_rect)
                if pix.width < 1 or pix.height < 1:
                    images.append(None)
                    continue
                    
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            except Exception:
                images.append(None)
    finally:
        pdf_document.close()

    return images


def crop_bboxes_to_base64_list(pdf_path: str, bbox_data: list[dict]) -> list[str | None]:
    images = _crop_bboxes_to_images(pdf_path, bbox_data)
    result: list[str | None] = []
    for img in images:
        if img is None:
            result.append(None)
            continue
        result.append(_image_to_base64(img))
    return result


class ImageCache:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS images (key TEXT PRIMARY KEY, base64 TEXT NOT NULL)"
                )
        except Exception:
            return

    def _make_key(self, pdf_path: str, page: int, bbox: list[float]) -> str:
        p = str(Path(_normalize_pdf_path(pdf_path)).expanduser().resolve())
        b = json.dumps(
            [round(float(x), 2) for x in bbox[:4]], separators=(",", ":")
        )
        return f"{p}::{int(page)}::{b}"

    def get(self, pdf_path: str, page: int, bbox: list[float]) -> str | None:
        key = self._make_key(pdf_path, page, bbox)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT base64 FROM images WHERE key = ?", (key,))
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            return None
        return None

    def set(self, pdf_path: str, page: int, bbox: list[float], base64_str: str) -> None:
        key = self._make_key(pdf_path, page, bbox)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO images (key, base64) VALUES (?, ?)",
                    (key, base64_str),
                )
        except Exception:
            return

    def set_batch(self, items: list[tuple[str, int, list[float], str]]) -> None:
        data = [
            (self._make_key(pdf_path, page, bbox), b64)
            for pdf_path, page, bbox, b64 in items
        ]
        if not data:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO images (key, base64) VALUES (?, ?)", data
                )
        except Exception:
            return


_image_cache_instance: ImageCache | None = None


def _get_image_cache() -> ImageCache | None:
    global _image_cache_instance
    if _image_cache_instance is not None:
        return _image_cache_instance
    try:
        settings = Settings.load()
        paths = resolve_paths(settings)
        db_path = paths.cache_dir / "image_cache.db"
        _image_cache_instance = ImageCache(db_path)
        return _image_cache_instance
    except Exception:
        return None


def crop_pdf_image_task(pdf_path: str, bbox_data: list[dict]) -> str:
    """Independent task function to crop images from PDF.

    This function is designed to be picklable and can run in an independent process.

    Args:
        pdf_path: Path to the PDF file.
        bbox_data: List of dictionaries containing 'page' (1-based) and 'bbox' [x0, y0, x1, y1].

    Returns:
        Base64 encoded string of the merged image.
    """
    images = _crop_bboxes_to_images(pdf_path, bbox_data)
    return _merge_images_to_base64(images)


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

        results: list[str] = []
        cache = _get_image_cache()

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
            if cache:
                images: list[Image.Image | None] = [None] * len(locs)
                missing: list[tuple[int, Location]] = []
                for idx, loc in enumerate(locs):
                    b64 = cache.get(str(path), loc.page, loc.bbox)
                    if b64:
                        img = _base64_to_image(b64)
                        if img is not None:
                            images[idx] = img
                            continue
                    missing.append((idx, loc))

                if missing:
                    bbox_data = [
                        {"page": loc.page, "bbox": loc.bbox} for _, loc in missing
                    ]
                    cropped = _crop_bboxes_to_images(str(path), bbox_data)
                    batch: list[tuple[str, int, list[float], str]] = []
                    for (idx, loc), img in zip(missing, cropped):
                        if img is None:
                            continue
                        images[idx] = img
                        b64 = _image_to_base64(img)
                        batch.append((str(path), loc.page, loc.bbox, b64))
                    if batch:
                        cache.set_batch(batch)

                if any(img is not None for img in images):
                    results.append(_merge_images_to_base64(images))
                    continue

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
