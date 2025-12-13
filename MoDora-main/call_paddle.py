from pathlib import Path
import json
import numpy as np
import fitz
from paddleocr import LayoutDetection, PaddleOCR
import os

# Initialize models
# Use LayoutDetection for accurate bboxes as requested
# Note: Initial load might take time
layout_model = LayoutDetection(model_name="PP-DocLayout_plus-L")
# Use PaddleOCR for text recognition within bboxes
ocr_model = PaddleOCR(use_angle_cls=True, lang="en") 

def paddle_generate(input_file, output_path):
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Run Layout Detection
    # predict() supports PDF input and iterates pages
    # batch_size=1 is safer for PDFs to avoid OOM and ensure order
    print(f"Running LayoutDetection on {input_file}...")
    layout_results = layout_model.predict(input_file, batch_size=1, layout_nms=True)
    
    # Open PDF for cropping and OCR
    doc = fitz.open(input_file)
    
    print(f"Processing {len(layout_results)} pages...")
    
    for i, res in enumerate(layout_results):
        if i >= len(doc):
            break
            
        # Get page image from PDF
        page = doc[i]
        pix = page.get_pixmap()
        # Convert to numpy array (Height, Width, Channels)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        # Convert to RGB if needed
        if pix.n == 4:
            img_array = img_array[:, :, :3] # Drop alpha
        elif pix.n == 1:
            # Grayscale to RGB
            img_array = np.repeat(img_array[:, :, np.newaxis], 3, axis=2)
        
        # Prepare result structure matching PPStructureV3
        parsing_res_list = []
        
        # Get boxes from result
        # LayoutDetection result 'res' is a dict-like object with 'boxes' key
        boxes = res['boxes'] if 'boxes' in res else []
        
        # Sort boxes by y, then x (top-down, left-right)
        boxes.sort(key=lambda x: (x['coordinate'][1], x['coordinate'][0]))
        
        for idx, box in enumerate(boxes):
            bbox = box['coordinate'] # [x1, y1, x2, y2]
            raw_label = box['label']
            
            # Map labels to MoDora expected types
            # PP-DocLayout labels: text, title, list, table, figure, doc_query, header, footer, reference
            # MoDora expects: paragraph_title, doc_title, image, chart, table, figure_title, header, footer, number, aside_text
            label = raw_label
            if raw_label == 'title':
                label = 'paragraph_title'
            elif raw_label == 'figure':
                label = 'image'
            elif raw_label in ['reference', 'list', 'doc_query', 'reference_content']:
                label = 'text' # Treat as body text
            
            # Crop image
            x1, y1, x2, y2 = map(int, bbox)
            # Clip to image bounds
            x1 = max(0, x1); y1 = max(0, y1)
            x2 = min(img_array.shape[1], x2); y2 = min(img_array.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            crop_img = img_array[y1:y2, x1:x2]
            
            # Run OCR
            # PaddleOCR.ocr takes numpy array
            # Removed cls=True as it caused TypeError, use_angle_cls=True in init should handle it
            try:
                # Ensure valid image for OCR
                if crop_img.size == 0 or crop_img.ndim != 3:
                    print(f"Skipping invalid crop: shape={crop_img.shape}")
                    continue
                    
                ocr_result = ocr_model.ocr(crop_img)
            except Exception as e:
                print(f"OCR failed for box {idx} on page {i}: {e}")
                ocr_result = []
            
            # Extract text
            rec_texts = []
            if ocr_result and isinstance(ocr_result, list) and len(ocr_result) > 0:
                # Check for PaddleX pipeline output format (list of dicts)
                if isinstance(ocr_result[0], dict) and 'rec_texts' in ocr_result[0]:
                     rec_texts = ocr_result[0]['rec_texts']
                # Fallback for standard PaddleOCR format (list of lists)
                elif isinstance(ocr_result[0], list):
                     for line in ocr_result[0]:
                         rec_texts.append(line[1][0])

            full_text = "\n".join(rec_texts)
            
            # Construct result item
            item = {
                "block_label": label,
                "block_content": full_text,
                "block_bbox": [float(c) for c in bbox], # Ensure standard float for JSON
                "block_id": idx,
                "block_order": idx + 1
            }
            parsing_res_list.append(item)
            
        # Construct full result dict
        page_res = {
            "input_path": str(input_file),
            "page_index": i,
            "parsing_res_list": parsing_res_list,
            # Add dummy model_settings
            "model_settings": {
                "use_doc_preprocessor": True,
                "use_seal_recognition": False,
                "use_table_recognition": True,
                "use_formula_recognition": True,
                "use_chart_recognition": True,
                "use_region_detection": True,
                "format_block_content": False
            }
        }
        
        # Save JSON
        # Filename convention: {basename}_{page_idx}_res.json
        basename = Path(input_file).stem
        json_filename = f"{basename}_{i}_res.json"
        with open(output_path / json_filename, "w", encoding="utf-8") as f:
            json.dump(page_res, f, ensure_ascii=False, indent=4)
            
    doc.close()
    print(f"Processing complete. Results saved to {output_path}")

def main():
    # Placeholder for testing
    pass

if __name__ == "__main__":
    main()
