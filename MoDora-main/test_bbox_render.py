import fitz
import json
import cv2
import numpy as np
import os
import glob

# Configuration
CACHE_DIR = "/home/yukai/project/MoDora/MoDora-main/cache/MMDA"
PDF_DIR = "/home/yukai/project/MoDora/datasets/MMDA"
OUTPUT_DIR = "/home/yukai/project/MoDora/MoDora-main/output/bbox_test"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def render_bbox(pdf_name, page_index):
    pdf_path = os.path.join(PDF_DIR, pdf_name)
    basename = os.path.splitext(pdf_name)[0]
    json_path = os.path.join(CACHE_DIR, basename, f"{basename}_{page_index}_res.json")
    
    if not os.path.exists(json_path):
        print(f"JSON not found: {json_path}")
        return

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    parsing_res_list = data.get('parsing_res_list', [])
    if not parsing_res_list:
        print(f"No bboxes in {json_path}")
        return

    # Load PDF
    doc = fitz.open(pdf_path)
    if page_index >= len(doc):
        print(f"Page {page_index} out of range for {pdf_name}")
        return
    page = doc[page_index]

    # LayoutDetection uses 2.0 scale (144 DPI) internally
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to image
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # Draw bboxes
    for item in parsing_res_list:
        bbox = item['block_bbox'] # [x1, y1, x2, y2]
        label = item['block_label']
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Draw rectangle
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        
        # Draw label
        cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    output_file = os.path.join(OUTPUT_DIR, f"{basename}_{page_index}.png")
    cv2.imwrite(output_file, img)
    print(f"Saved: {output_file}")

# Process 1.pdf, 2.pdf, 3.pdf (First page only for quick check)
for pdf_file in ["1.pdf", "2.pdf", "3.pdf"]:
    render_bbox(pdf_file, 0)
