import base64
from PIL import Image
import io
import fitz


def _normalize_pdf_path(pdf_path: str) -> str:
    """Normalize the path format to be compatible with fitz.open.

    Handles the 'file:/path/to.pdf' URI scheme by stripping the 'file:' prefix
    if present.

    Args:
        pdf_path (str): The input PDF path, which may include a 'file:' prefix.

    Returns:
        str: The normalized file path.
    """
    p = (pdf_path or "").strip()
    if p.startswith("file:"):
        p = p[len("file:") :]
    return p


def crop_pdf_image_task(pdf_path: str, bbox_data: list[dict]) -> str:
    pdf_path = _normalize_pdf_path(pdf_path)
    try:
        pdf_document = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return ""

    images = []
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
        return ""

    total_width = max(int(img.width) for img in images)
    total_height = sum(int(img.height) for img in images)
    merged_image = Image.new("RGB", (total_width, total_height))

    y_offset = 0
    for img in images:
        merged_image.paste(img, (0, y_offset))
        y_offset += int(img.height)

    # Resize if too large (e.g. > 1024x1024)
    MAX_SIZE = 1024
    if merged_image.width > MAX_SIZE or merged_image.height > MAX_SIZE:
        merged_image.thumbnail((MAX_SIZE, MAX_SIZE), Image.Resampling.LANCZOS)

    # Save to file for debugging
    output_filename = "debug_crop_output.png"
    merged_image.save(output_filename)
    print(f"Saved cropped image to {output_filename}")
    print(f"Image size: {merged_image.size}")

    buffered = io.BytesIO()
    merged_image.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.read()).decode("utf-8")


# Data from the tree.json
pdf_path = "/home/yukai/project/MoDora/datasets/MMDA/1.pdf"
bbox_data = [
    {"bbox": [66.5, 181.5, 530.0, 333.5], "page": 3},
    {"bbox": [66.5, 373.0, 530.5, 491.5], "page": 3},
    {"bbox": [65.5, 532.0, 530.0, 617.5], "page": 3},
    {"bbox": [66.5, 658.0, 529.0, 743.5], "page": 3},
]

if __name__ == "__main__":
    b64 = crop_pdf_image_task(pdf_path, bbox_data)
    print(f"Base64 length: {len(b64)}")
