from pathlib import Path
import json
import numpy as np
import fitz
from paddleocr import LayoutDetection, PaddleOCR, PPStructureV3
import os
import cv2

# Initialize models
pp_structure = PPStructureV3(
    device="gpu:2",
    use_table_recognition=False,
    lang='en',
    layout_unclip_ratio=0.5
)

layout_model = LayoutDetection(
    model_name="PP-DocLayout_plus-L",
    device="gpu:2"
)

def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU).
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
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    
    union_area = area1 + area2 - intersection_area
    if union_area == 0:
        return 0.0
        
    return intersection_area / union_area

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
        pp_iter = pp_structure.predict_iter(img_array)
        pp_res = next(pp_iter)
        
        pp_results = []
        if 'parsing_res_list' in pp_res:
            pp_results = pp_res['parsing_res_list']
        elif 'region_det_res' in pp_res:
            pp_results = pp_res['region_det_res']
        if isinstance(pp_results, tuple):
            pp_results = pp_results[0]
            
        # 2. Run LayoutDetection for Accurate BBoxes
        # Note: layout_model must be defined in the global scope
        layout_res = layout_model.predict(img_array)
        layout_boxes = []
        for res in layout_res:
            if 'boxes' in res:
                layout_boxes.extend(res['boxes'])
            break
        
        # 3. Robust Fusion matching
        parsing_res_list = []
        
        # Convert PP results to a more usable list of dicts with calculated bboxes
        pp_blocks = []
        for idx, pp_region in enumerate(pp_results):
            pp_bbox = getattr(pp_region, 'bbox', None) or getattr(pp_region, 'layout_bbox', None)
            pp_type = getattr(pp_region, 'type', None) or getattr(pp_region, 'label', None) or getattr(pp_region, 'layout_label', 'text')
            text_val = getattr(pp_region, 'text', None) or getattr(pp_region, 'rec_text', None) or getattr(pp_region, 'content', None)
            
            rec_texts = []
            if text_val:
                rec_texts.append(text_val)
            else:
                res_val = getattr(pp_region, 'res', None)
                if res_val:
                    for line in res_val:
                        if isinstance(line, dict) and 'text' in line:
                            rec_texts.append(line['text'])
                        elif (isinstance(line, tuple) or isinstance(line, list)) and len(line) >= 1 and isinstance(line[0], str):
                            rec_texts.append(line[0])
            
            if pp_bbox:
                pp_blocks.append({
                    'id': idx,
                    'bbox': pp_bbox,
                    'type': str(pp_type).lower(),
                    'text': "\n".join(rec_texts)
                })

        print(f"Page {i}: PPStructure found {len(pp_blocks)} blocks, LayoutDetection found {len(layout_boxes)} blocks.")
        
        # 3.1 Global Alignment (Optional but recommended if coordinates differ significantly)
        if len(pp_blocks) > 0 and len(layout_boxes) > 0:
            # Calculate global bounds for PP
            pp_min_x = min(b['bbox'][0] for b in pp_blocks)
            pp_min_y = min(b['bbox'][1] for b in pp_blocks)
            pp_max_x = max(b['bbox'][2] for b in pp_blocks)
            pp_max_y = max(b['bbox'][3] for b in pp_blocks)
            pp_w = pp_max_x - pp_min_x
            pp_h = pp_max_y - pp_min_y
            
            # Calculate global bounds for Layout
            ld_min_x = min(b['coordinate'][0] for b in layout_boxes)
            ld_min_y = min(b['coordinate'][1] for b in layout_boxes)
            ld_max_x = max(b['coordinate'][2] for b in layout_boxes)
            ld_max_y = max(b['coordinate'][3] for b in layout_boxes)
            ld_w = ld_max_x - ld_min_x
            ld_h = ld_max_y - ld_min_y
            
            print(f"Alignment Bounds - PP: [{pp_min_x}, {pp_min_y}, {pp_max_x}, {pp_max_y}], LD: [{ld_min_x}, {ld_min_y}, {ld_max_x}, {ld_max_y}]")
            
            if pp_w > 0 and pp_h > 0:
                for b in pp_blocks:
                    # Map PP bbox to Layout space
                    b['aligned_bbox'] = [
                        (b['bbox'][0] - pp_min_x) * (ld_w / pp_w) + ld_min_x,
                        (b['bbox'][1] - pp_min_y) * (ld_h / pp_h) + ld_min_y,
                        (b['bbox'][2] - pp_min_x) * (ld_w / pp_w) + ld_min_x,
                        (b['bbox'][3] - pp_min_y) * (ld_h / pp_h) + ld_min_y
                    ]
            else:
                for b in pp_blocks: b['aligned_bbox'] = b['bbox']
        else:
            for b in pp_blocks: b['aligned_bbox'] = b['bbox']

        # Track which layout boxes are used
        used_layout_indices = set()

        # Match PP blocks to Layout boxes
        for pp_idx, pp_block in enumerate(pp_blocks):
            best_score = -1.0
            best_layout_idx = -1
            
            target_bbox = pp_block['aligned_bbox']
            target_center = [(target_bbox[0] + target_bbox[2]) / 2, (target_bbox[1] + target_bbox[3]) / 2]
            
            for l_idx, l_box in enumerate(layout_boxes):
                l_bbox = l_box['coordinate']
                iou = calculate_iou(target_bbox, l_bbox)
                
                # Calculate normalized distance score (1.0 = same center, 0.0 = very far)
                l_center = [(l_bbox[0] + l_bbox[2]) / 2, (l_bbox[1] + l_bbox[3]) / 2]
                dist = np.sqrt((target_center[0] - l_center[0])**2 + (target_center[1] - l_center[1])**2)
                # Use page diagonal as normalization factor
                diag = np.sqrt(ld_w**2 + ld_h**2)
                dist_score = max(0, 1.0 - (dist / (diag * 0.2))) # 20% of diagonal is the "reach"
                
                # Combined score: IoU has higher priority, but distance breaks ties or helps when IoU is 0
                score = iou * 2.0 + dist_score
                
                if score > best_score:
                    best_score = score
                    best_layout_idx = l_idx
            
            # GUARANTEE MAPPING: Always pick the best layout box if available
            if best_layout_idx != -1 and best_score > 0.1: # Threshold to ensure it's a "meaningful" match
                final_bbox = layout_boxes[best_layout_idx]['coordinate']
                used_layout_indices.add(best_layout_idx)
                match_type = "layout_graft"
            else:
                # ABSOLUTE PRESERVATION: Use aligned PP bbox if no good layout box found
                # This ensures the content is NEVER dropped and coordinates are still aligned to Layout space
                final_bbox = pp_block['aligned_bbox']
                match_type = "pp_aligned"
            
            # Label mapping
            label = pp_block['type']
            if label == 'title': label = 'paragraph_title'
            elif label == 'figure': label = 'image'
            elif label == 'equation': label = 'text'
            
            parsing_res_list.append({
                "block_label": label,
                "block_content": pp_block['text'],
                "block_bbox": [float(c) for c in final_bbox],
                "block_id": pp_block['id'],
                "block_order": pp_idx + 1,
                "match_type": match_type
            })

        # Sort by top-to-bottom, then left-to-right
        parsing_res_list.sort(key=lambda x: (x['block_bbox'][1], x['block_bbox'][0]))
        for idx, item in enumerate(parsing_res_list):
            item['block_order'] = idx + 1

        page_res = {
            "input_path": str(input_file),
            "page_index": i,
            "parsing_res_list": parsing_res_list,
            "model_settings": {"use_region_detection": True}
        }
        
        # Save JSON
        basename = Path(input_file).stem
        json_filename = f"{basename}_{i}_res.json"
        with open(output_path / json_filename, "w", encoding="utf-8") as f:
            json.dump(page_res, f, ensure_ascii=False, indent=4)
        
        # 4. Visualization
        img_vis = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        for item in parsing_res_list:
            bbox = item['block_bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Color code: Blue for grafted, Red for preserved aligned PP
            color = (255, 0, 0) if item.get('match_type') == "layout_graft" else (0, 0, 255)
            
            cv2.rectangle(img_vis, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img_vis, f"{item['block_order']}:{item['block_label']}", (x1, y1-5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        vis_filename = f"{basename}_{i}_vis.png"
        cv2.imwrite(str(output_path / vis_filename), img_vis)
        print(f"Saved visualization to {output_path / vis_filename}")
            
    doc.close()
    print(f"Processing complete. Results saved to {output_path}")

def main():
    # Example for testing
    from constants import BASE_DIR
    sample_pdf = Path(BASE_DIR) / "4.pdf"
    output_dir = Path("./output_test")
    if sample_pdf.exists():
        paddle_generate(str(sample_pdf), str(output_dir))
    else:
        print(f"File not found: {sample_pdf}")

if __name__ == "__main__":
    main()
