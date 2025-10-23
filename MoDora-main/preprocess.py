import os
import json
import re

from pydantic import BaseModel, Field
from call_paddle import paddle_generate
from constants import *
from qwen_call import qwen_annotation
from api_utils import bbox_to_base64

import pypandoc
from markdownify import markdownify as md

def cp_init(cp_type="",title="",metadata="",data="",location=None):
    # Create a component
    cp = {
        'type': cp_type,
        'title': title,
        'metadata': metadata,
        'data': data,
        'location': [] if not location else location
    }
    return cp

def get_components(source_path, cache_path):
    # Initial sequence
    bbox_list = []
    cp_dict = {
        'body':[],
        'supplement':{}
    }
    header = {}
    footer = {}
    number = {}
    aside = {}
    
    # Load OCR results
    page_cnt = 1
    files = os.listdir(cache_path)
    pattern = re.compile(r'^(.+)_(\d+)_res\.json$')
    matching_files = [filename for filename in files if pattern.match(filename)]
    matching_files = sorted(matching_files, key=lambda x: int(pattern.match(x).group(2)))
    print(matching_files)

    for file in matching_files:
        with open(os.path.join(cache_path, file), 'r', encoding='utf-8') as f:
            page = json.load(f)
        
        for bbox in page['parsing_res_list']:
            bbox['page_id'] = page_cnt
            bbox_list.append(bbox)
        page_cnt = page_cnt + 1
    

    # Traverse in reading order
    list_cnt = 0
    text_cp_cnt = 0
    cur_text_title = "Default Title"
    cur_figure_title = "Default Title"
    non_text_cache = []
    cur_text_cp = cp_init(cp_type="text", metadata = text_cp_cnt, title = cur_text_title)
    for bbox in bbox_list:
        # A1: Title + (0-x) paragraphs
        if bbox['block_label'] in ["paragraph_title","doc_title"]:
            cur_text_title = bbox['block_content']

            # Append the last one with image/chart/table
            if cur_text_cp['title'] != "Default Title" or cur_text_cp['data'] != "":
                cp_dict['body'].append(cur_text_cp)
                text_cp_cnt = text_cp_cnt + 1
            cp_dict['body'] = cp_dict['body'] + non_text_cache

            # Create the new one
            non_text_cache = []
            cur_text_cp = cp_init(cp_type="text", title = cur_text_title, metadata = text_cp_cnt, location = [{'range':bbox['block_bbox'], 'page':bbox['page_id']}])
        
        # A2: (0-1) Title + image/chart/table
        elif bbox['block_label'] in ["image", "chart", "table"]:
            cur_figure_cp = cp_init(cp_type=bbox['block_label'], metadata = text_cp_cnt, location = [{'range':bbox['block_bbox'], 'page':bbox['page_id']}])
            
            # Not assigned title before it
            if list_cnt>0 and bbox_list[list_cnt-1]['block_label'] == "figure_title" and bbox_list[list_cnt-1]['block_content'] != cur_figure_title:
                cur_figure_title = bbox_list[list_cnt-1]['block_content']
                cur_figure_cp['location'].append({'range':bbox_list[list_cnt-1]['block_bbox'], 'page':bbox_list[list_cnt-1]['page_id']})

            # Title after it
            elif list_cnt<len(bbox_list)-1 and bbox_list[list_cnt+1]['block_label'] == "figure_title":
                cur_figure_title = bbox_list[list_cnt+1]['block_content']
                cur_figure_cp['location'].append({'range':bbox_list[list_cnt+1]['block_bbox'], 'page':bbox_list[list_cnt+1]['page_id']})

            # No adjacent titles
            else:
                cur_figure_title = "Default Title"
            
            cur_figure_cp['title'] = cur_figure_title
            non_text_cache.append(cur_figure_cp) # Not directly append to maintain the reading order

        elif bbox['block_label'] == "figure_title":
            None
        
        # A3: Supplementary elements
        elif bbox['block_label'] == "header":
            if f"Header of Page {bbox['page_id']}" not in header:
                header[f"Header of Page {bbox['page_id']}"] = {'type':"header", 'metadata':"", 'data':bbox['block_content'], 'location':[{'range':bbox['block_bbox'], 'page':bbox['page_id']}]}
            else:
                header[f"Header of Page {bbox['page_id']}"]['data'] = header[f"Header of Page {bbox['page_id']}"]['data'] + bbox['block_content']
                header[f"Header of Page {bbox['page_id']}"]['location'].append({'range':bbox['block_bbox'], 'page':bbox['page_id']})

        elif bbox['block_label'] == "footer":
            if f"Footer of Page {bbox['page_id']}" not in footer:
                footer[f"Footer of Page {bbox['page_id']}"] = {'type':"footer", 'metadata':"", 'data':bbox['block_content'], 'location':[{'range':bbox['block_bbox'], 'page':bbox['page_id']}]}
            else:
                footer[f"Footer of Page {bbox['page_id']}"]['data'] = footer[f"Footer of Page {bbox['page_id']}"]['data'] + bbox['block_content']
                footer[f"Footer of Page {bbox['page_id']}"]['location'].append({'range':bbox['block_bbox'], 'page':bbox['page_id']})

        elif bbox['block_label'] == "number":
            if f"Original number of Page {bbox['page_id']}" not in number:
                number[f"Original number of Page {bbox['page_id']}"] = {'type':"number", 'metadata':"", 'data':bbox['block_content'], 'location':[{'range':bbox['block_bbox'], 'page':bbox['page_id']}]}
            else:
                number[f"Original number of Page {bbox['page_id']}"]['data'] = number[f"Original number of Page {bbox['page_id']}"]['data'] + bbox['block_content']
                number[f"Original number of Page {bbox['page_id']}"]['location'].append({'range':bbox['block_bbox'], 'page':bbox['page_id']})

        elif bbox['block_label'] == "aside_text":
            if f"Aside text of Page {bbox['page_id']}" not in aside:
                aside[f"Aside text of Page {bbox['page_id']}"] = {'type':"aside_text", 'metadata':"", 'data':bbox['block_content'], 'location':[{'range':bbox['block_bbox'], 'page':bbox['page_id']}]}
            else:
                aside[f"Aside text of Page {bbox['page_id']}"]['data'] = aside[f"Aside text of Page {bbox['page_id']}"]['data'] + bbox['block_content']
                aside[f"Aside text of Page {bbox['page_id']}"]['location'].append({'range':bbox['block_bbox'], 'page':bbox['page_id']})

        else:
            # Collect paragraphs for A1
            cur_text_cp['data'] = cur_text_cp['data'] + f"\n\n {bbox['block_content']}"
            cur_text_cp['location'].append({'range':bbox['block_bbox'], 'page':bbox['page_id']})

        list_cnt = list_cnt + 1
    
    # Append the tail and supplements
    if cur_text_cp['title'] != "Default Title" or cur_text_cp['data'] != "":
        cp_dict['body'].append(cur_text_cp)

    cp_dict['body'] = cp_dict['body'] + non_text_cache

    cp_dict['supplement']['header'] = header
    cp_dict['supplement']['footer'] = footer
    cp_dict['supplement']['number'] = number
    cp_dict['supplement']['aside'] = aside

    # Template-Based Information Enrichment
    for cp in cp_dict['body']:
        if cp['type'] in ["image", "chart", "table"]:
            title, metadata, data = information_enrichment(source_path, cp['location'], cp['type'])
            cp['title'] = title if cp['title'] == "Default Title" else cp['title']
            cp['metadata'] = metadata
            cp['data'] = data if cp['data'] == "" else cp['data']
    
    return cp_dict
    

def information_enrichment(source_path, location, cp_type):
    base64_figure = bbox_to_base64(source_path, location)
    return qwen_annotation(base64_figure, cp_type)

def preprocess(source_path,cache_dir):
    # Prepare
    cache_path = os.path.join(cache_dir, os.path.splitext(os.path.basename(source_path))[0])
    os.makedirs(cache_path, exist_ok=True)
    cp_path = os.path.join(cache_path, "cp.json")

    try:
        # OCR-based preprocess
        paddle_generate(source_path, cache_path)
        cp_dict = get_components(source_path, cache_path)
        
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        cp_dict = {
            'body':[],
            'supplement':{}
        }
    
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(cp_dict, f, ensure_ascii=False, indent=4)