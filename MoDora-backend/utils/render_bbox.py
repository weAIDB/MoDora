import argparse
import json
import os
import fitz  # PyMuPDF
import random

def get_random_color():
    return (random.random(), random.random(), random.random())

def draw_bboxes(pdf_path, tree_data, output_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return

    # Collect leaf nodes with bboxes
    leaf_nodes = []
    
    def traverse(node):
        if "children" in node and node["children"]:
            for child in node["children"].values():
                traverse(child)
        else:
            # It's a leaf node (or at least has no children in this structure)
            if "location" in node and node["location"]:
                leaf_nodes.append(node)

    traverse(tree_data)

    print(f"Found {len(leaf_nodes)} leaf nodes with locations.")

    for node in leaf_nodes:
        color = get_random_color()
        for loc in node["location"]:
            page_num = loc.get("page")
            bbox = loc.get("bbox")
            
            if page_num is not None and bbox:
                # Page number is 1-based in tree.json usually, fitz is 0-based
                page_idx = page_num - 1
                if 0 <= page_idx < len(doc):
                    page = doc[page_idx]
                    rect = fitz.Rect(bbox)
                    
                    # Draw rectangle
                    shape = page.new_shape()
                    shape.draw_rect(rect)
                    shape.finish(color=color, width=1.5)
                    
                    # Draw text label (optional, maybe node type or metadata snippet)
                    node_type = node.get("type", "unknown")
                    shape.insert_text(rect.tl, node_type, fontsize=8, color=color)
                    
                    shape.commit()

    doc.save(output_path)
    print(f"Rendered PDF saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Render leaf node bboxes on PDF.")
    parser.add_argument("pdf_id", help="The ID of the PDF (e.g., 305)")
    parser.add_argument("--cache_dir", default="/home/yukai/project/MoDora/MoDora-backend/cache_v6", help="Path to cache directory")
    parser.add_argument("--pdf_dir", default="/home/yukai/project/MoDora/datasets/MMDA", help="Path to original PDF directory")
    
    args = parser.parse_args()
    
    pdf_id = args.pdf_id
    cache_path = os.path.join(args.cache_dir, pdf_id)
    tree_path = os.path.join(cache_path, "tree.json")
    
    # Try to find the PDF. It might be pdf_id.pdf or we might need to look it up if mapping was complex,
    # but based on previous context, cache_v6 IDs match MMDA filenames.
    pdf_path = os.path.join(args.pdf_dir, f"{pdf_id}.pdf")
    
    if not os.path.exists(tree_path):
        print(f"Error: tree.json not found at {tree_path}")
        return
        
    if not os.path.exists(pdf_path):
        print(f"Error: PDF not found at {pdf_path}")
        return

    try:
        with open(tree_path, 'r', encoding='utf-8') as f:
            tree_data = json.load(f)
    except Exception as e:
        print(f"Error reading tree.json: {e}")
        return

    output_pdf_path = os.path.join(cache_path, f"{pdf_id}_rendered.pdf")
    
    draw_bboxes(pdf_path, tree_data, output_pdf_path)

if __name__ == "__main__":
    main()
