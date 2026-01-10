import copy
import os
import json
import re
import ast
from api_utils import *
from prompt_template import *

import threading
from concurrent.futures import ThreadPoolExecutor, Future
import math
from logger import logger

def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value

def generate_levels(raw_title_list, base64_image, config=None):
    prompt = title_extract_prompt.format(raw_list = raw_title_list)
    if config:
        res = gpt_generate_pdf(
            base64_image, prompt, 
            key=config.get('apiKey') or API_KEY, 
            url=config.get('baseUrl') or API_URL, 
            base_model=config.get('treeModel') or MODEL
        )
    else:
        res = gpt_generate_pdf(base64_image, prompt)
    return res

def generate_metadata(data, n0, config=None):
    prompt = metadata_generation_prompt.format(data = data, n0 = n0)
    if config:
        res = gpt_generate(
            prompt, 
            key=config.get('apiKey') or API_KEY, 
            url=config.get('baseUrl') or API_URL, 
            base_model=config.get('treeModel') or MODEL
        )
    else:
        res = gpt_generate(prompt)
    return ';'.join(res.split(';')[:n0])

def integrate_metadata(data, number, config=None):
    prompt = metadata_integration_prompt.format(data = data, number = number)
    if config:
        res = gpt_generate(
            prompt, 
            key=config.get('apiKey') or API_KEY, 
            url=config.get('baseUrl') or API_URL, 
            base_model=config.get('treeModel') or MODEL
        )
    else:
        res = gpt_generate(prompt)
    return ';'.join(res.split(';')[:number])

def calculate_n_i(D_i, d_i, n_im1, k = 2):
    # log2(n_{i-1}^k)
    log_part = math.log2(n_im1 ** k)
    
    # (D_i + d_i - 1) / D_i
    fraction_part = (D_i + d_i - 1) / D_i
    
    # final
    n_i = fraction_part * log_part + 1
    
    return math.ceil(n_i)

def get_metadata(root, level = 1, n0 = 2, max_workers = 16, config=None):
    # Concurrent metadata generation
    sem = threading.BoundedSemaphore(value=max_workers)

    def _compute(node, level, executor):
        if not node:
            return 0, 1, 1

        # Initial parameters
        n_children = 0
        n = n0
        d = 1
        D = 1

        if 'children' not in node:
             logger.warning(f"!!! Warning: Node missing children: {node.keys()} Type: {node.get('type')}")
             node['children'] = {}

        children = list(node['children'].values())

        # 1. Submit children tasks (Parallel)
        results = []
        for child in children:
            if sem.acquire(blocking=False):
                def _task(c=child, lv=level+1):
                    try:
                        return _compute(c, lv, executor)
                    finally:
                        sem.release()
                results.append(executor.submit(_task))
            else:
                results.append(_compute(child, level + 1, executor))

        # 2. Process self metadata (Parallel with children)
        # Run in current thread to avoid deadlock and utilize waiting time
        node_type = node.get('type')
        if node_type == 'text':
             # Generate self metadata immediately
             node['metadata'] = generate_metadata(node['data'], n0, config=config)

        # 3. Gather children results
        for item in results:
            if isinstance(item, Future):
                n_child, d_child, D_child = item.result()
            else:
                n_child, d_child, D_child = item
            d = max(d, d_child)
            D = max(D, D_child)
            n_children += n_child

        # 4. Integration
        if node_type == "text" or node_type == "root": 
            # Note: node['metadata'] for text is already generated above
            
            if n_children > 0:
                n = calculate_n_i(D, d, n_children)
                # 如果是 root，可能没有 data 字段作为基础，仅依赖 children 的 metadata
                base_meta = node.get('metadata', '') 
                data = [base_meta] + [c['metadata'] for c in children]
                node['metadata'] = integrate_metadata(data, n, config=config)
            # For leaf text
            else:
                D = level
        # For others 
        else:
            node['metadata'] = node['data'] if node['metadata'] == "" else node['metadata']
            D = level

        return n, d + 1, D

    # Top execution
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return _compute(root, level, executor)

def construct(cp_dict):
    
    # Initialize the root and stack
    root = {
            'type': "root",
            'metadata':"", 
            'data': "",
            'location': [],
            'children': {}
        }
    stack = [{'node': root, 'level': -1}]
    
    # Traverse in reading order
    for cp in cp_dict['body']:
        
        # Create node
        current_node = {
            'type': cp['type'],
            'metadata': cp['metadata'], 
            'data': cp['data'],
            'location': cp['location'],
            'children': {}
        }
        
        # For text
        if cp['type'] == 'text':
            title = cp['title']
            level = cp['title_level']
        
            # Pop until a higher level (small number)
            while stack[-1]["level"] >= level:
                stack.pop()
            parent = stack[-1]["node"]
        
            # Link to the parent
            cnt = 1
            if cp['title'] not in parent["children"]:
                parent["children"][cp['title']] = current_node
            else:
                while (cp['title'] + f"_{cnt}") in parent["children"]:
                    cnt = cnt + 1 # Avoid duplicate names
                parent["children"][cp['title'] + f"_{cnt}"] = current_node
            
            # Push
            stack.append({"node": current_node, "level": level})

        # For image, table and chart
        elif cp['type'] in ['image', 'table', 'chart']:

            parent = stack[-1]["node"]
            cnt = 1
            if cp['title'] not in parent["children"]:
                parent["children"][cp['title']] = current_node
            else:
                while (cp['title'] + f"_{cnt}") in parent["children"]:
                    cnt = cnt + 1 # Avoid duplicate names
                parent["children"][cp['title'] + f"_{cnt}"] = current_node

    # Separated branch for supplement
    for page_header in cp_dict['supplement']['header'].values():
        page_header['metadata'] = page_header['data']
        page_header['children'] = {}
    for page_footer in cp_dict['supplement']['footer'].values():
        page_footer['metadata'] = page_footer['data']
        page_footer['children'] = {}
    for page_number in cp_dict['supplement']['number'].values():
        page_number['metadata'] = page_number['data']
        page_number['children'] = {}
    for page_aside in cp_dict['supplement']['aside'].values():
        page_aside['metadata'] = page_aside['data']
        page_aside['children'] = {}
    header_root = {
            'type': "header",
            'metadata': "Record header information in the document", 
            'data': "",
            'location': [],
            'children': cp_dict['supplement']['header']
        }
    footer_root = {
            'type': "footer",
            'metadata': "Record footer information in the document", 
            'data': "",
            'location': [],
            'children': cp_dict['supplement']['footer']
        }
    number_root = {
            'type': "number",
            'metadata': "Record original number of pages in the document", 
            'data': "",
            'location': [],
            'children': cp_dict['supplement']['number']
        }
    aside_root = {
            'type': "aside_text",
            'metadata': "Record aside text in the document", 
            'data': "",
            'location': [],
            'children': cp_dict['supplement']['aside']
        }
    supplement_root = {
            'type': "supplement",
            'metadata': "Record supplement information like header, footer, original page number and aside text in the document", 
            'data': "",
            'location': [],
            'children': {'header': header_root, 'footer':footer_root, 'number':number_root, 'aside':aside_root}
        }
    root['children']['Supplement'] = supplement_root

    return root

def build_tree(source_path, cache_dir, config=None):
    # Prepare
    cache_path = os.path.join(cache_dir, os.path.splitext(os.path.basename(source_path))[0])
    cp_path = os.path.join(cache_path, "cp.json")
    tree_path = os.path.join(cache_path,"tree.json")
    title_path = os.path.join(cache_path,"title.json")
    
    try:
        with open(cp_path, "r", encoding="utf-8") as f:
            cp_dict = json.load(f)

    except Exception as e:
        logger.error(f"Fail to load components when constructing tree: {e}")
        return

    if not cp_dict:
        title_list = []
        cctree = {}
        
    else:
        try:
            # Hierarchy detection in preprocessing
            text_cp = [item for item in cp_dict['body'] if item['type'] == 'text']
            raw_title_list = [cp['title'] for cp in text_cp]
            title_bbox_list = [cp['location'][0] for cp in text_cp]

            base64_image = bbox_to_base64(source_path, title_bbox_list)
            try:
                title_list = ast.literal_eval(generate_levels(raw_title_list, base64_image, config=config))
                with open(title_path, "w", encoding="utf-8") as f:
                    json.dump(title_list, f, ensure_ascii=False, indent=4)
            except Exception as e:
                title_list = []

            for i in range(len(raw_title_list)):
                if i >= len(title_list):
                    text_cp[i]['title_level'] = 1
                else:
                    s = title_list[i]
                    text_cp[i]['title_level'] = len(s.lstrip()) - len(s.lstrip().lstrip('#'))
            
            # Construction
            cctree = construct(cp_dict)
        except Exception as e:
            logger.error(f"!!! Error in build_tree logic: {e}")
            title_list = []
            cctree = {}
        
        # Summarization
        if config is not None:
            get_metadata(cctree, config=config)
        
    with open(tree_path, "w", encoding="utf-8") as f:
        json.dump(cctree, f, ensure_ascii=False, indent=4)

    with open(title_path, "w", encoding="utf-8") as f:
        json.dump(title_list, f, ensure_ascii=False, indent=4)
