import os
import json
from tqdm import tqdm
import multiprocessing
import time

from constants import *
from logger import logger
from preprocess import preprocess
from cctree import build_tree
from prompt_template import *
from qa import *

from concurrent.futures import ThreadPoolExecutor, as_completed

PROCESS_RANGE = 1, 200

def pipeline(id, source_path, cache_dir, query="", log_dir = None, use_cache=False, config=None):
    # Prepare
    cache_path = os.path.join(cache_dir, os.path.splitext(os.path.basename(source_path))[0])
    cp_path = os.path.join(cache_path, "cp.json")
    tree_path = os.path.join(cache_path,"tree.json")
    title_path = os.path.join(cache_path,"title.json")
    if log_dir != None:
        log_path = os.path.join(log_dir, f"{id}_log.txt")
        # Create a simple logger object that qa() expects
        class SimpleLogger:
            def __init__(self, path):
                self.path = path
            def info(self, msg):
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(str(msg) + "\n")
        
        log_file = SimpleLogger(log_path)
        # Clear log file
        with open(log_path, "w", encoding="utf-8") as f:
            pass
    else:
        log_file = None
    if not use_cache:
        # Preprocessing
        preprocess(source_path, cache_dir, config=config)
        # Tree construction
        build_tree(source_path, cache_dir, config=config)

    cctree = {}
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            cctree = json.load(f)

    except Exception as e:
        logger.error(f"Fail to read from cache: {e}")
        return ""
    
    # Tree based analysis
    final_answer = qa(cctree, query, log_file, source_path, config=config)
    return final_answer
    

def process_item(item, processed_docs, source_dir, pipeline, cache_dir, log_dir, enable_cache):
    try:
        source_path = os.path.join(source_dir, item["pdf_id"])
        query = item["question"]
        id = item["questionId"]
        doc_id = item["pdf_id"]

        # Skip processed documents
        use_cache = doc_id in processed_docs
        if not use_cache:
            processed_docs[doc_id] = source_path
        else:
            source_path = processed_docs[doc_id]

        # Pipeline processing
        answer = pipeline(id, source_path, cache_dir, query, log_dir, use_cache or enable_cache)
        item['prediction'] = answer
        return item
    except Exception as e:
        logger.error(f"Error processing item {item}: {e}")
        return None

def run_on_dataset(source_dir, cache_dir, log_dir = None, output_dir = None, enable_cache = False):
    # Prepare
    with open(os.path.join(source_dir, "test.json"), "r", encoding="utf-8") as f:
        dataset = json.load(f)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    
    sorted_data = sorted(dataset, key=lambda x: x["questionId"])
    
    # Filter for 1.pdf to 200.pdf
    target_pdfs = {f"{i}.pdf" for i in range(PROCESS_RANGE[0], PROCESS_RANGE[1]+1)}
    sorted_data = [item for item in sorted_data if item["pdf_id"] in target_pdfs]
    
    # sorted_data = sorted_data[:0] # Few samples test

    results = []
    processed_docs = {}

    # Concurrent processing with cache
    workers = 4 if enable_cache else 1
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_item = {
            executor.submit(process_item, item, processed_docs, source_dir, pipeline, cache_dir, log_dir, enable_cache): item
            for item in sorted_data
        }

        for future in tqdm(as_completed(future_to_item), desc="Processing dataset:", total=len(sorted_data)):
            item = future_to_item[future]
            try:
                result = future.result()
                if result is not None:
                    results.append(result)

                    # Real-time results collection and storage
                    with open(os.path.join(output_dir, "res.json"), "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"Error in future for item {item}: {e}")

def main():
    source_dir = BASE_DIR
    cache_dir = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    log_dir = os.path.join(LOG_DIR, os.path.basename(BASE_DIR))
    output_dir = os.path.join(OUTPUT_DIR, os.path.basename(BASE_DIR))
    enable_cache = ENABLE_CACHE
    run_on_dataset(source_dir, cache_dir, log_dir, output_dir, enable_cache)


if __name__ == "__main__":
    main()