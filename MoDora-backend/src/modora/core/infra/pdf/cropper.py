from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import fitz
from PIL import Image

from modora.core.domain.component import Component, Location
from modora.core.interfaces.media import ImageProvider

# 如果裁剪失败（PDF打不开/页号越界/bbox非法等），返回 1x1 空白 PNG 的 base64。
_BLANK_1X1_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAFh4kXcAAAAASUVORK5CYII="


def _normalize_pdf_path(pdf_path: str) -> str:
    """兼容 source=file:/path/to.pdf 的形式，供 fitz.open 使用。"""
    p = (pdf_path or "").strip()
    if p.startswith("file:"):
        p = p[len("file:") :]
    return p


def bbox_to_base64(pdf_path: str, bbox_list: list[Location]) -> str:
    """
    将 PDF 中多个 bbox 区域裁剪出来并拼接为一张 PNG，然后返回 base64。

    Args:
        pdf_path: PDF 文件路径 (支持 "file:" 前缀)
        bbox_list: 包含多个 Location 的列表，每个 Location 表示一个要裁剪的区域

    Returns:
        str: Base64 编码的 PNG 图片
    """
    pdf_path = _normalize_pdf_path(pdf_path)
    pdf_document = fitz.open(pdf_path)

    images: list[Image] = []
    for loc in bbox_list:
        # OCR 的 page_id 从 1 开始，这里转换成 fitz 的 0-based page index。
        page_idx = loc.page - 1
        crop_range = loc.bbox
        page = pdf_document[page_idx]

        pix = page.get_pixmap(clip=crop_range)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    if not images:
        raise ValueError("No specific image!!!")

    total_width = max(int(img.width) for img in images)
    total_height = sum(int(img.height) for img in images)
    merged_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for img in images:
        merged_image.paste(img, (0, y_offset))
        y_offset += int(img.height)

    buffered = io.BytesIO()
    merged_image.save(buffered, format="PNG")
    buffered.seek(0)
    pdf_document.close()
    return base64.b64encode(buffered.read()).decode("utf-8")


def render_ocr_json_to_pdf(
    ocr_json_path: str, out_pdf_path: str | None = None, pdf_path: str | None = None
) -> str:
    """把 OCR 输出 JSON 中的 bbox/label 渲染回 PDF 页面，输出标注后的 PDF。"""
    ocr_p = Path(ocr_json_path)
    obj = json.loads(ocr_p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise TypeError("ocr json must be an object")

    if pdf_path is None:
        src = obj.get("source")
        if not isinstance(src, str) or not src.startswith("file:"):
            raise ValueError("pdf_path not provided and source is not file:<path>")
        pdf_path = src[len("file:") :]

    if out_pdf_path is None:
        out_pdf_path = str(ocr_p.with_suffix("")) + ".rendered.pdf"

    blocks = obj.get("blocks")
    if not isinstance(blocks, list):
        raise TypeError("blocks must be a list")

    def color_for(label: str) -> tuple[float, float, float]:
        palette = [
            (1.0, 0.0, 0.0),
            (0.0, 0.6, 0.0),
            (0.0, 0.3, 1.0),
            (1.0, 0.5, 0.0),
            (0.6, 0.0, 0.8),
            (0.0, 0.7, 0.7),
        ]
        idx = abs(hash(label)) % len(palette)
        return palette[idx]

    doc = fitz.open(pdf_path)
    try:
        for b in blocks:
            if not isinstance(b, dict):
                continue
            page_id = b.get("page_id")
            bbox = [x for x in b.get("bbox")]
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
    """
    PDF 图片裁剪适配器。
    实现了 ImageProvider 接口，使用 PyMuPDF (fitz) 从 PDF 中裁剪指定区域。
    """

    def crop_image(self, source: str, locs: Component | list[Location]) -> str:
        """
        从 PDF 文件中裁剪组件区域并转换为 Base64 图片。

        Args:
            source: PDF 文件路径 (支持 "file:" 前缀)
            component: 包含位置信息的组件

        Returns:
            str: Base64 编码的 PNG 图片
        """
        if isinstance(locs, Component):
            locs = locs.location
        return bbox_to_base64(source, locs)
