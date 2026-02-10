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


def crop_pdf_image_task(pdf_path: str, bbox_data: list[dict]) -> str:
    """
    从 PDF 中裁剪图像的独立任务函数。
    该函数设计为可序列化的（picklable），可以在独立进程中运行。

    参数:
        pdf_path: PDF 文件路径。
        bbox_data: 包含 'page' (从1开始) 和 'bbox' [x0, y0, x1, y1] 的字典列表。

    返回:
        合并后图像的 Base64 编码字符串。
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

    # 如果图像太大（例如 > 1024x1024），进行缩放
    # 限制最大尺寸以减少 token 消耗
    MAX_SIZE = 1024
    if merged_image.width > MAX_SIZE or merged_image.height > MAX_SIZE:
        merged_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    buffered = io.BytesIO()
    merged_image.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.read()).decode("utf-8")


def bbox_to_base64(pdf_path: str, bbox_list: list[Location]) -> str:
    """
    为了向后兼容的包装函数。
    注意：直接调用此函数会在当前进程/线程中运行，这对于 fitz 来说可能不安全。
    建议在并发场景下配合 ProcessPoolExecutor 使用 crop_pdf_image_task。
    """
    bbox_data = [{"page": loc.page, "bbox": loc.bbox} for loc in bbox_list]
    return crop_pdf_image_task(pdf_path, bbox_data)


def render_ocr_json_to_pdf(
    ocr_json_path: str, out_pdf_path: str | None = None, pdf_path: str | None = None
) -> str:
    """
    把 OCR 输出 JSON 中的 bbox/label 渲染回 PDF 页面，输出标注后的 PDF。
    """
    ocr_p = Path(ocr_json_path)
    obj = json.loads(ocr_p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise TypeError("OCR JSON 必须是一个对象")

    if pdf_path is None:
        src = obj.get("source")
        if not isinstance(src, str) or not src.startswith("file:"):
            raise ValueError("未提供 pdf_path 且 source 不是 file:<path> 格式")
        pdf_path = src[len("file:") :]

    if out_pdf_path is None:
        out_pdf_path = str(ocr_p.with_suffix("")) + ".rendered.pdf"

    blocks = obj.get("blocks")
    if not isinstance(blocks, list):
        raise TypeError("blocks 必须是一个列表")

    def color_for(label: str) -> tuple[float, float, float]:
        """为不同的标签生成固定的颜色。"""
        palette = [
            (1.0, 0.0, 0.0),  # 红色
            (0.0, 0.6, 0.0),  # 绿色
            (0.0, 0.3, 1.0),  # 蓝色
            (1.0, 0.5, 0.0),  # 橙色
            (0.6, 0.0, 0.8),  # 紫色
            (0.0, 0.7, 0.7),  # 青色
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

    def crop_image(
        self,
        source_path: str | dict[str, str],
        locations: list[Location],
        file_names: list[str] | None = None,
    ) -> list[str]:
        """
        根据位置信息裁剪图像。
        支持单文档或多文档。如果是多文档，locations 中应包含正确的 file_name。

        Args:
            source_path: PDF 路径或文件名到路径的映射。
            locations: 待裁剪的位置列表。
            file_names: 可选的文件名列表，如果提供且 locations 中 file_name 为空，则默认使用第一个。

        Returns:
            裁剪后的 Base64 图像列表。
        """
        if not locations:
            return []

        # 简单的实现：按文件分组裁剪，然后返回 base64 列表
        # 在实际的多文档 RAG 中，通常我们会返回一个大的拼接图或多张图
        # 这里为了兼容现有 reason_retrieved 接口，我们返回多张裁剪图
        results = []

        # 分组
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

            # 使用现有的 bbox_to_base64 (同步版本，QAService 目前是同步调用它的)
            # 注意：后期可以考虑优化为异步
            img_b64 = bbox_to_base64(str(path), locs)
            results.append(img_b64)

        return results

    def pdf_to_base64(self, source: str) -> str:
        """
        将整个 PDF（所有页面）转换为单个垂直堆叠的 Base64 图像。
        """
        source = _normalize_pdf_path(source)
        try:
            doc = fitz.open(source)
        except Exception:
            return _BLANK_1X1_PNG_BASE64

        # 为每一页创建全页 bbox
        bbox_data = []
        for i, page in enumerate(doc):
            rect = page.rect
            bbox_data.append(
                {"page": i + 1, "bbox": [rect.x0, rect.y0, rect.x1, rect.y1]}
            )
        doc.close()

        return crop_pdf_image_task(source, bbox_data)
