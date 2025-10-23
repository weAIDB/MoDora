import ast
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from api_utils import *
from prompt_template import *
from constants import *
from qwen_call import call_qwen_em

def bool_string(s):
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False

def check_node(data, query):
    prompt = check_node_prompt1.format(data=data, query=query)
    res = gpt_generate(prompt)
    return bool_string(res)

def check_node_mm(data, retrieved_image, query):
    prompt = check_node_prompt2.format(data=data, query=query)
    res = gpt_generate(prompt)
    return bool_string(res)

def select_children(list, query ,path="None", metadata_map="None"):
    prompt = select_children_prompt.format(list=list, query=query, path=path, metadata_map=metadata_map)
    res = gpt_generate(prompt)
    return res

log_lock = threading.Lock()
def _safe_log(log_file, *lines):
    if not log_file:
        return
    try:
        with log_lock:
            with open(log_file, "a", encoding="utf-8") as f:
                for ln in lines:
                    f.write(str(ln) + ("\n" if not str(ln).endswith("\n") else ""))
    except Exception:
        pass

def _process_excluded_key(excluded_key, path, node, query, log_file):
    # Fallback embedding search and verification for not selected subtree
    try:
        embed_res = call_qwen_em(query, node['children'][excluded_key]) # Em Search
        if check_node(embed_res, query) is True: # LLM Verification
            s_path = path + "--" + excluded_key # Record path
            _safe_log(log_file,
                      f"{DELIMITER} Embedding Search Result {DELIMITER}",
                      f"{s_path}: {embed_res}")
            return s_path, embed_res
    except Exception as e:
        print(f"Fallback fails: {e}")
    return None

def _process_single_node(path, node, query, log_file, source_path, executor, inner_max_workers=None):
    # Forward search and backward verification for a node
    retrieve_result = {}
    retrieve_bbox = {}
    selected_children = {}

    try:
        base_path = path.split('--')[-1] if '--' in path else path

        # Backward verification
        if node['type'] != 'root':
            base64_image = bbox_to_base64(source_path, node['location'])
            if check_node_mm(base_path + ": " + node['data'], base64_image, query):
                retrieve_result[path] = node['data'] # Textual evidence
                retrieve_bbox[path] = node['location'] # Locational evidence

        if len(node['children']) == 0:
            return retrieve_result, retrieve_bbox, selected_children
        
        # Forward search
        keys = list(node['children'].keys())
        metadata_map = {key: node['children'][key]['metadata'] for key in keys}

        title_list = []
        if keys:
            try:
                # LLM select
                title_list = ast.literal_eval(select_children(keys, query, path, metadata_map))
            except Exception:
                title_list = []

            _safe_log(log_file, f"{DELIMITER} Select Children {DELIMITER}", f"{title_list}")

            # Concurrent fallback
            excluded_keys = [x for x in keys if x not in title_list]
            futs = []

            with ThreadPoolExecutor(max_workers=inner_max_workers) as inner_executor:
                futs = [inner_executor.submit(_process_excluded_key, ek, path, node, query, log_file)
                        for ek in excluded_keys]
                for fut in as_completed(futs):
                    res = fut.result()
                    if res:
                        s_path, embed_res = res
                        if s_path not in retrieve_result:
                            retrieve_result[s_path] = ""
                        retrieve_result[s_path] = (retrieve_result[s_path] + "\n" + embed_res).strip()

            # Collect selected nodes for the next iteration
            for key in title_list:
                child_node = node['children'][key]
                selected_children[path + "--" + key] = child_node # Record path

    except Exception as e:
        print(f"Retrieve on node {path} fails: {e}")

    return retrieve_result, retrieve_bbox, selected_children


def select_and_check_by_level(cur_level, query, log_file, source_path, max_workers=2, inner_max_workers=2):
    retrieve_result = {}
    retrieve_bbox = {}
    selected_children = {}

    if not cur_level:
        return retrieve_result, retrieve_bbox
    
    # Concurrent execution on current-level nodes
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _process_single_node,
                path, node, query, log_file, source_path, executor, inner_max_workers
            ): path
            for path, node in cur_level.items()
        }

        for fut in as_completed(futures):
            try:
                rr, rb, sc = fut.result()
                retrieve_result.update(rr)
                retrieve_bbox.update(rb)
                selected_children.update(sc)
            except Exception as e:
                print(f"节点处理失败: {futures[fut]} -> {e}")

    # Go to the next level
    sub_result, sub_bbox = select_and_check_by_level(
        selected_children, query, log_file, source_path,
        max_workers=max_workers, inner_max_workers=inner_max_workers
    )
    retrieve_result.update(sub_result)
    retrieve_bbox.update(sub_bbox)

    return retrieve_result, retrieve_bbox

def retrieve_by_location(tree, page_list, position_vector, pdf_path):
    # Retrive based on locations
    pdf_document = fitz.open(pdf_path)

    retrieved_text = {}
    retrieved_bbox = {}
    
    # For each page
    def traverse_tree(node, path, page_number, position_vector):
        nonlocal retrieved_text, retrieved_bbox
        
        # Fetch the page
        page = pdf_document[page_number - 1]
        page_width, page_height = page.rect.width, page.rect.height
        
        # Check the location of the current node
        if 'location' in node:
            for loc in node['location']:

                # Check page index
                if loc['page'] == page_number:

                    # Check the grid specified by the position vector
                    bbox = loc['range']
                    row, column = position_vector

                    # Normalized coordinaries
                    normalized_x0 = bbox[0] / (2*page_width)
                    normalized_y0 = bbox[1] / (2*page_height)
                    normalized_x1 = bbox[2] / (2*page_width)
                    normalized_y1 = bbox[3] / (2*page_height)

                    # 3x3 grids
                    grid_x0 = (column - 1) / 3 if column != -1 else 0
                    grid_x1 = column / 3 if column != -1 else 1
                    grid_y0 = (row - 1) / 3 if row != -1 else 0
                    grid_y1 = row / 3 if row != -1 else 1

                    # The judgment of overlap
                    x_overlap = not (normalized_x1 <= grid_x0 or normalized_x0 >= grid_x1)
                    y_overlap = not (normalized_y1 <= grid_y0 or normalized_y0 >= grid_y1)

                    if x_overlap and y_overlap:
                        if path not in retrieved_text:
                            retrieved_text[path] = node['data']
                            retrieved_bbox[path] = []
                        retrieved_bbox[path].append(loc)

        # Recursively check children
        if 'children' in node:
            for child_key, child_node in node['children'].items():
                child_path = f"{path}--{child_key}"
                traverse_tree(child_node, child_path, page_number,
                              position_vector)

    # Retrive by page
    if -1 in page_list:
        doc_len = pdf_document.page_count
        page_list = list(range(1, doc_len + 1))
    for page_number in page_list:
        for key, root_node in tree.items():
            traverse_tree(root_node, key, page_number, position_vector)
    
    pdf_document.close()
    return retrieved_text, retrieved_bbox

def retrieve_by_semantics(query, cctree, source_path, log_file=False):
    # Retrive based on titles, metadata and data
    retrieve_result = select_and_check_by_level({"root":cctree}, query, log_file, source_path)
    return retrieve_result

