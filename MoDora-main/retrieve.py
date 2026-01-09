import ast
import traceback
import fitz  # PyMuPDF
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from api_utils import *
from prompt_template import *
from constants import *
from logger import logger
from qwen_call import call_qwen_em

def bool_string(s):
    s = s.lower()
    if "t" in s or "yes" in s or "true" in s:
        return True
    return False

def check_node(data, query, config=None):
    prompt = check_node_prompt1.format(data=data, query=query)
    
    key = config.get('apiKey') if config and config.get('apiKey') else API_KEY
    url = config.get('baseUrl') if config and config.get('baseUrl') else API_URL
    base_model = config.get('qaModel') if config and config.get('qaModel') else MODEL
    
    res = gpt_generate(prompt, key=key, url=url, base_model=base_model)
    return bool_string(res)

def check_node_mm(data, retrieved_image, query, config=None):
    prompt = check_node_prompt2.format(data=data, query=query)
    
    key = config.get('apiKey') if config and config.get('apiKey') else API_KEY
    url = config.get('baseUrl') if config and config.get('baseUrl') else API_URL
    base_model = config.get('qaModel') if config and config.get('qaModel') else MODEL
    
    res = gpt_generate(prompt, key=key, url=url, base_model=base_model)
    return bool_string(res)

def select_children(keys, query ,path="None", metadata_map="None", config=None):
    prompt = select_children_prompt.format(list=keys, query=query, path=path, metadata_map=metadata_map)
    
    key = config.get('apiKey') if config and config.get('apiKey') else API_KEY
    url = config.get('baseUrl') if config and config.get('baseUrl') else API_URL
    base_model = config.get('qaModel') if config and config.get('qaModel') else MODEL
    
    res = gpt_generate(prompt, key=key, url=url, base_model=base_model)
    return res

def _safe_log(log_file, *lines):
    if not log_file:
        return
    try:
        for ln in lines:
            log_file.info(str(ln))
    except Exception:
        pass

def check_location(node, source_path, locations, only_self = False):
    # Use node-specific source path if available
    current_source_path = node.get('source_path', source_path)
    if not current_source_path:
        return False, []

    pdf_document = fitz.open(current_source_path)
    page_count = pdf_document.page_count
    within_locs = []
    flag = False
    
    # 处理倒数页面计数和无页面信息的情况
    new_locations = []
    for location in locations:
        if location['page'] == 0:
            grids = location['grids']
            for x in range(1, page_count+1):
                new_locations.append({'page':x, 'grids':grids})
        elif location['page'] < 0:
            new_page = page_count + location['page'] + 1
            if new_page < 1 or new_page > page_count:
                new_page = 1
            location['page'] = new_page
    
    locations = [location for location in locations if location['page'] != 0] + new_locations

    # 正式处理页面和位置信息
    for location in locations:
        page_number = location['page']
        position_vectors = location['grids'] if location['grids'] else [(-1, -1)]
    
        page = pdf_document[page_number - 1]
        page_width, page_height = page.rect.width, page.rect.height
        
        # Check the location of the current node
        if 'location' in node:
            for loc in node['location']:

                # Check page index
                if loc['page'] == page_number:

                    # Check the grid specified by the position vector
                    bbox = loc['range']
                    for position_vector in position_vectors:
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
                            flag = True
                            within_locs.append(loc)
                            break
    if flag:
        return flag, within_locs
    
    pdf_document.close()

    # Recursively check children
    if not only_self and 'children' in node:
        for child_node in node['children'].values():
            child_res, _ = check_location(child_node, current_source_path, locations)
            if child_res:
                return True, []

    return False, []

def filt_by_location(node, source_path, locations):
    # Use node-specific source path if available
    current_source_path = node.get('source_path', source_path)

    # Retrive based on locations
    if not locations:
        return list(node['children'].keys())

    filted_keys = []
    for key, child_node in node['children'].items():
        child_res, _ = check_location(child_node, current_source_path, locations)
        if child_res:
            filted_keys.append(key)

    return filted_keys

def _process_excluded_key(excluded_key, path, node, query, log_file, config=None):
    # Fallback embedding search and verification for not selected subtree
    try:
        embed_res = call_qwen_em(query, node['children'][excluded_key]) # Em Search
        if check_node(embed_res, query, config=config) is True: # LLM Verification
            s_path = path + "--" + excluded_key # Record path
            _safe_log(log_file,
                      f"{DELIMITER} Embedding Search Result {DELIMITER}",
                      f"{s_path}: {embed_res}")
            return s_path, embed_res
    except Exception as e:
        logger.error(f"Fallback fails: {e}")
        return None

def _process_single_node(path, node, query, log_file, source_path, locations, inner_max_workers=None, config=None):
    # Forward search and backward verification for a node
    retrieve_result = {}
    retrieve_bbox = {}
    selected_children = {}
    node_impacts = {}

    try:
        base_path = path.split('--')[-1] if '--' in path else path
        
        # Use node-specific source path if available
        current_source_path = node.get('source_path', source_path)

        # Backward verification
        curloc_res, within_locs = check_location(node, current_source_path, locations, True)
        if node['type'] != 'root' and node['type'] != 'MROOT' and curloc_res:
            base64_image = bbox_to_base64(current_source_path, within_locs)
            if check_node_mm(base_path + ": " + node['data'], base64_image, query, config=config):
                retrieve_result[path] = node['data'] # Textual evidence
                node_impacts[path] = node_impacts.get(path, 0) + 5
                # Inject source_path into locations
                for loc in within_locs:
                    loc['source_path'] = current_source_path
                retrieve_bbox[path] = within_locs # Locational evidence

        if len(node['children']) == 0:
            return retrieve_result, retrieve_bbox, selected_children, node_impacts
        
        # Forward search
        keys = filt_by_location(node, current_source_path, locations) # list(node['children'].keys())
        metadata_map = {key: node['children'][key]['metadata'] for key in keys}

        title_list = []
        if keys:
            try:
                # LLM select
                title_list = ast.literal_eval(select_children(keys, query, path, metadata_map, config=config))
            except Exception:
                title_list = []

            _safe_log(log_file, f"{DELIMITER} Select Children {DELIMITER}", f"{title_list}")
            
            '''
            # Concurrent fallback
            excluded_keys = [x for x in keys if x not in title_list]
            futs = []

            with ThreadPoolExecutor(max_workers=inner_max_workers) as inner_executor:
                futs = [inner_executor.submit(_process_excluded_key, ek, path, node, query, log_file, config=config)
                        for ek in excluded_keys]
                for fut in as_completed(futs):
                    res = fut.result()
                    if res:
                        s_path, embed_res = res
                        if s_path not in retrieve_result:
                            retrieve_result[s_path] = ""
                        retrieve_result[s_path] = (retrieve_result[s_path] + "\n" + embed_res).strip()
            '''

            # Collect selected nodes for the next iteration
            for key in title_list:
                if key in node['children']:
                    child_node = node['children'][key]
                    # Inject source_path for the next level if not present
                    if 'source_path' not in child_node:
                        child_node['source_path'] = current_source_path
                    
                    child_path = path + "--" + key
                    selected_children[child_path] = child_node # Record path
                    node_impacts[child_path] = node_impacts.get(child_path, 0) + 1

    except Exception as e:
        logger.error(f"Retrieval on node {path} fails: {e}")
        # traceback.print_exc()
        return {}, {}, {}, {}

    return retrieve_result, retrieve_bbox, selected_children, node_impacts


def select_and_check_by_level(cur_level, query, log_file, source_path, locations, max_workers=4, inner_max_workers=4, config=None):
    retrieve_result = {}
    retrieve_bbox = {}
    selected_children = {}
    node_impacts = {}

    if not cur_level:
        return retrieve_result, retrieve_bbox, node_impacts
    
    # Concurrent execution on current-level nodes
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _process_single_node,
                path, node, query, log_file, source_path, locations, inner_max_workers, config
            ): path
            for path, node in cur_level.items()
        }

        for fut in as_completed(futures):
            try:
                rr, rb, sc, ni = fut.result()
                retrieve_result.update(rr)
                retrieve_bbox.update(rb)
                selected_children.update(sc)
                
                # Merge node_impacts
                for k, v in ni.items():
                    node_impacts[k] = node_impacts.get(k, 0) + v
                    
            except Exception as e:
                logger.error(f"Retrieval fails: {futures[fut]} -> {e}")

    # Go to the next level
    sub_result, sub_bbox, sub_impacts = select_and_check_by_level(
        selected_children, query, log_file, source_path, locations,
        max_workers=max_workers, inner_max_workers=inner_max_workers, config=config
    )
    retrieve_result.update(sub_result)
    retrieve_bbox.update(sub_bbox)
    
    # Merge sub_impacts
    for k, v in sub_impacts.items():
        node_impacts[k] = node_impacts.get(k, 0) + v

    return retrieve_result, retrieve_bbox, node_impacts


'''
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
'''

def retrieve(query, cctree, source_path, locations=None, log_file=None, config=None):
    # Retrive based on titles, metadata and data
    retrieve_result, retrieve_bbox, node_impacts = select_and_check_by_level({"root":cctree}, query, log_file, source_path, locations, config=config)
    return retrieve_result, retrieve_bbox, node_impacts

