import os
import json
import shutil
from pathlib import Path
from difflib import SequenceMatcher

def get_text_from_json(json_path, file_type):
    if not os.path.exists(json_path):
        return ""
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        text_content = ""
        # Try to get text from body
        if "body" in data and isinstance(data["body"], list):
            for item in data["body"]:
                if item.get("type") == "text":
                    text_content += item.get("data", "") + "\n"
                    # Get enough text
                    if len(text_content) > 1000:
                        break
        return text_content
    except Exception as e:
        print(f"Error reading {file_type} {json_path}: {e}")
        return ""

def main():
    cache_v5_dir = "/home/yukai/project/MoDora/MoDora-backend/cache_v5"
    cache_old_dir = "/home/yukai/project/MoDora/MoDora-backend/cache_old"
    cache_v6_dir = "/home/yukai/project/MoDora/MoDora-backend/cache_v6"
    output_mapping_file = "/home/yukai/project/MoDora/MoDora-backend/utils/cache_mapping_v6.json"
    
    # Ensure cache_v6 exists
    os.makedirs(cache_v6_dir, exist_ok=True)
    
    v5_dirs = [d for d in Path(cache_v5_dir).iterdir() if d.is_dir()]
    cache_old_dirs = [d for d in Path(cache_old_dir).iterdir() if d.is_dir()]
    
    print(f"Found {len(v5_dirs)} dirs in cache_v5 and {len(cache_old_dirs)} dirs in cache_old.")
    
    # Pre-load cache_old texts (cp.json)
    old_cache_texts = {}
    print("Loading texts from cache_old (cp.json)...")
    for d in cache_old_dirs:
        text = get_text_from_json(os.path.join(d, "cp.json"), "cp.json")
        if text.strip():
            old_cache_texts[d.name] = text
            
    mapping = {}
    
    print("Matching cache_v5 (co.json) to cache_old (cp.json)...")
    
    processed_count = 0
    match_count = 0
    
    for v5_dir in v5_dirs:
        v5_id = v5_dir.name
        
        # Check if already processed in v6
        target_dir = os.path.join(cache_v6_dir, v5_id)
        # if os.path.exists(target_dir):
        #     print(f"Skipping {v5_id}, already exists in v6")
        #     continue

        v5_text = get_text_from_json(os.path.join(v5_dir, "co.json"), "co.json")
        
        if not v5_text.strip():
            print(f"Warning: No text found in cache_v5/{v5_id}/co.json")
            continue
            
        best_match = None
        best_ratio = 0.0
        
        # Take first 500 chars for faster comparison, usually enough for identification
        v5_sample = " ".join(v5_text.split()[:500])
        
        for old_name, old_text in old_cache_texts.items():
            old_sample = " ".join(old_text.split()[:500])
            
            ratio = SequenceMatcher(None, v5_sample, old_sample).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = old_name
        
        processed_count += 1
        
        if best_ratio > 0.3: # Threshold
            print(f"Match found: {v5_id} -> {best_match} (Score: {best_ratio:.2f})")
            mapping[v5_id] = best_match
            match_count += 1
            
            # Copy files to cache_v6
            source_dir = os.path.join(cache_old_dir, best_match)
            
            # Create target directory
            os.makedirs(target_dir, exist_ok=True)
            
            # Copy all files from source to target
            try:
                for item in os.listdir(source_dir):
                    s = os.path.join(source_dir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                    elif os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
            except Exception as e:
                print(f"Error copying files for {v5_id}: {e}")
                
        else:
            print(f"No match found for {v5_id} (Best score: {best_ratio:.2f})")

    # Save mapping
    with open(output_mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
        
    print(f"Processing complete. Processed: {processed_count}, Matched: {match_count}")
    print(f"Mapping saved to {output_mapping_file}")

if __name__ == "__main__":
    main()
