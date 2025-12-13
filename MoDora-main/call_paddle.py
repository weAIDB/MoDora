from pathlib import Path
import json
import numpy as np
import fitz
from paddleocr import LayoutDetection, PaddleOCR, PPStructureV3
import os
import cv2

# Initialize models
# Use LayoutDetection for accurate bboxes
layout_model = LayoutDetection(model_name="PP-DocLayout_plus-L")
# Use PPStructure for tree structure and content
# Adapted for PPStructureV3 signature
# User requested layout_unclip_ratio
pp_structure = PPStructureV3(use_table_recognition=False, lang='en', layout_unclip_ratio=0.5)

def calculate_overlap_ratio(box1, box2):
    """
    Calculate Intersection over Area of Box1 (Overlap Ratio).
    Box format: [x1, y1, x2, y2]
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    x_left = max(x1_1, x1_2)
    y_top = max(y1_1, y1_2)
    x_right = min(x2_1, x2_2)
    y_bottom = min(y2_1, y2_2)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    
    if area1 == 0:
        return 0.0
        
    return intersection_area / area1

def paddle_generate(input_file, output_path):
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {input_file}...")
    
    # Open PDF
    doc = fitz.open(input_file)
    
    for i in range(len(doc)):
        print(f"Processing page {i}...")
        page = doc[i]
        
        # Render page to image with 2x zoom (consistent with LayoutDetection's preferred scale and frontend expectation)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array (H, W, C)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_array = img_array[:, :, :3] # Drop alpha
        elif pix.n == 1:
            img_array = np.repeat(img_array[:, :, np.newaxis], 3, axis=2) # Grayscale to RGB
            
        # 1. Run PPStructure for Structure & Content
        # PPStructure expects an image array
        pp_iter = pp_structure.predict_iter(img_array)
        pp_res = next(pp_iter)
        # pp_res is a StructureResult object, check keys or access parsing_res_list
        # According to inspection: keys include 'parsing_res_list'
        
        # We need to extract regions from pp_res['parsing_res_list'] (or equivalent)
        # The structure of parsing_res_list items needs to be handled
        
        # Note: parsing_res_list in PPStructureV3 (PaddleX) might already be the final list
        # but we need to check if it contains 'bbox' and 'type' keys matching our logic
        
        # Let's inspect the first item if available to adjust logic dynamically
        pp_results = []
        if 'parsing_res_list' in pp_res:
             pp_results = pp_res['parsing_res_list']
        elif 'region_det_res' in pp_res:
             pp_results = pp_res['region_det_res']
             
        # PPStructureV3 parsing_res_list items might be different from V2
        # Usually they contain 'layout_bbox' (or just 'bbox') and 'rec_text' (or 'text')
        
        # 2. Run LayoutDetection for Accurate BBoxes
        # LayoutDetection predict takes image array
        # Note: predict() returns a generator or list depending on input. 
        # When passing a single image array, it might return a single result object or a list.
        layout_res = layout_model.predict(img_array)
        # Check result format
        layout_boxes = []
        # layout_res is usually a generator for list of inputs, or a single result dict
        # Based on previous code, it returns a list-like object. 
        # Since we pass one image, we expect one result.
        # However, layout_model.predict might handle list of images.
        # Let's inspect layout_res. If it's a generator, consume it.
        
        current_layout_boxes = []
        try:
            # Handle generator or list
            for res in layout_res:
                if 'boxes' in res:
                    current_layout_boxes.extend(res['boxes'])
                # If we passed single image, we might get just one result item
                break 
        except TypeError:
             # If it's not iterable, maybe it's the result dict itself?
             if isinstance(layout_res, dict) and 'boxes' in layout_res:
                 current_layout_boxes = layout_res['boxes']

        # 3. Fuse Results
        # Iterate over PPStructure blocks and find matching LayoutDetection block
        
        parsing_res_list = []
        
        # Handle PPStructure output format
        # It usually returns a list of dicts, or a tuple (res, time)
        # If recovery=True, it returns a list of sorted regions
        # Each region: {'type': '...', 'bbox': [x1, y1, x2, y2], 'img': ..., 'res': ...}
        
        # Ensure pp_results is a list of regions
        if isinstance(pp_results, tuple):
             pp_results = pp_results[0]
             
        for idx, pp_region in enumerate(pp_results):
            # Debug: print dir of first region
            # if idx == 0:
            #     print(f"DEBUG: PPStructure region dir: {dir(pp_region)}")
                
            # Access attributes using getattr since it's an object
            pp_bbox = getattr(pp_region, 'bbox', None) or getattr(pp_region, 'layout_bbox', None)
            pp_type = getattr(pp_region, 'type', None) or getattr(pp_region, 'label', None) or getattr(pp_region, 'layout_label', 'text')
            
            if pp_bbox is None:
                print(f"Warning: Skipping region {idx} without bbox")
                continue
            
            # Find best match in LayoutDetection results
            best_ratio = 0.0
            best_layout_bbox = None
            
            for l_box in current_layout_boxes:
                l_bbox = l_box['coordinate']
                # Calculate overlap ratio (intersection / pp_area)
                ratio = calculate_overlap_ratio(pp_bbox, l_bbox)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_layout_bbox = l_bbox
            
            # If match found (Ratio > 0.5), use LayoutDetection bbox
            # If no match, SKIP this region entirely (User request: do not keep PPStructure coordinates)
            if best_ratio > 0.5 and best_layout_bbox is not None:
                final_bbox = best_layout_bbox
            else:
                # Try to relax if it's a large containment?
                # If ratio > 0.1, maybe accept?
                # But strictly adhering to "LayoutDetection bbox is accurate"
                if best_ratio > 0.1 and best_layout_bbox is not None:
                     final_bbox = best_layout_bbox
                else:
                     # print(f"Skipping region {idx} due to low overlap ({best_ratio:.2f})")
                     continue
            
            # Extract Text
            rec_texts = []
            # Handle V3 'res' or direct text field using getattr
            # 'content' seems to be the attribute holding text in LayoutBlock
            text_val = getattr(pp_region, 'text', None) or getattr(pp_region, 'rec_text', None) or getattr(pp_region, 'content', None)
            
            if text_val:
                rec_texts.append(text_val)
            else:
                res_val = getattr(pp_region, 'res', None)
                if res_val:
                    # V2 format or list
                    for line in res_val:
                        if isinstance(line, dict) and 'text' in line:
                            rec_texts.append(line['text'])
                        elif isinstance(line, tuple) or isinstance(line, list):
                            if len(line) >= 1 and isinstance(line[0], str):
                                rec_texts.append(line[0])
            
            full_text = "\n".join(rec_texts)
            
            # Map Labels
            # PPStructure labels: text, title, list, table, figure, header, footer, reference, equation
            # MoDora labels: paragraph_title, doc_title, image, chart, table, figure_title, header, footer, number, aside_text
            
            label = str(pp_type).lower() if pp_type else 'text'
            if label == 'title':
                label = 'paragraph_title'
            elif label == 'figure':
                label = 'image'
            elif label == 'equation':
                 label = 'text' # Or formula if supported
            
            # Construct result item
            item = {
                "block_label": label,
                "block_content": full_text,
                "block_bbox": [float(c) for c in final_bbox],
                "block_id": idx,
                "block_order": idx + 1
            }
            parsing_res_list.append(item)

        # Construct full result dict
        page_res = {
            "input_path": str(input_file),
            "page_index": i,
            "parsing_res_list": parsing_res_list,
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
