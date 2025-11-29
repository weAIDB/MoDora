import re
import ast
import json
from api_utils import *
from prompt_template import *
from constants import *
from retrieve import *
from concurrent.futures import ThreadPoolExecutor, as_completed

def simplify_tree(cctree):
    for index, sub_tree in cctree.items():
        del sub_tree['type']
        del sub_tree['metadata']
        simplify_tree(sub_tree['children'])

def get_tree_schema(cctree):
    schema = {}
    for index, sub_tree in cctree.items():
        if index != "Supplement":
            sub_tree_schema = get_tree_schema(sub_tree['children'])     
            schema[index] = sub_tree_schema
    return schema

def whole_reason(whole_doc, query, cctree):
    prompt = whole_reasoning_prompt.format(query=query,data=cctree)
    res = gpt_generate(prompt)
    return res

def retrieved_reason(query, retrieved_text, retrieved_image, schema):
    prompt = retrieved_reasoning_prompt.format(query=query, evidence=retrieved_text, schema=schema)
    res = gpt_generate(prompt)
    return res

def check_answer(query, answer):
    prompt = check_answer_prompt.format(query=query, answer=answer)
    res = gpt_generate(prompt)
    return bool_string(res)

def parse_response(resp):
    """
    解析大模型返回的响应，提取location和content信息
    
    Args:
        resp: 大模型返回的字符串，格式如：
              "-question: ...\n-location: [{\"page\":1, \"grid\":[\"(2, 2)\"]}]\n-content: ..."
    
    Returns:
        dict: 包含解析后的location和content
    """
    try:
        question_match = re.search(r'-question:\s*(.*?)(?=\n-location:|\Z)', resp, re.DOTALL)
        location_match = re.search(r'-location:\s*(.*?)(?=\n-content:|\Z)', resp, re.DOTALL)
        content_match = re.search(r'-content:\s*(.*)', resp, re.DOTALL)
        
        if not all([question_match, location_match, content_match]):
            lines = resp.strip().split('\n')
            parsed = {}
            for line in lines:
                if line.startswith('-question:'):
                    parsed['question'] = line.replace('-question:', '').strip()
                elif line.startswith('-location:'):
                    parsed['location_str'] = line.replace('-location:', '').strip()
                elif line.startswith('-content:'):
                    parsed['content'] = line.replace('-content:', '').strip()
            
            location_str = parsed.get('location_str', '[]')
        else:
            location_str = location_match.group(1).strip()
            content = content_match.group(1).strip()

        location_str = re.sub(r'\s+', ' ', location_str).strip()
        
        # 解析JSON
        location_data = json.loads(location_str)

        for location in location_data:
            tuple_list = [ast.literal_eval(s) for s in location['grid']]
            location['grids'] = tuple_list
            del location['grid']
        
        return {
            'location': location_data,
            'content': content_match.group(1).strip() if content_match else parsed.get('content', '')
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"原始location字符串: {location_str}")
        return {'location': [], 'content': ''}
    except Exception as e:
        print(f"解析响应时出错: {e}")
        return {'location': [{'page':0, 'grids':[]}], 'content': ''}

def question_parsing(question):
    prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", question)
    res = gpt_generate(prompt)
    return parse_response(res)

def qa(cctree, query, log_file=None, source_path=False):

    if log_file is not None:    # Log
        with open(log_file, "a") as f:
            f.write(
                f"{DELIMITER} Answering Query {DELIMITER}\n"
            )
            f.write(f"{query}\n")

    answer = "None"
    parsed_res = question_parsing(query)
    locations = parsed_res['location']
    query = parsed_res['content']

    if log_file is not None:    # Log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"{DELIMITER} Location Cues {DELIMITER}\n"
            )
            f.write(f"{locations}\n")
    if log_file is not None:    # Log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"{DELIMITER} Semantic Cues {DELIMITER}\n"
            )
            f.write(f"{query}\n")

    
    # 结合位置和语义的 Retrieve
    retrieved_text, retrieved_bbox = retrieve(query=query, cctree=cctree, source_path=source_path, locations=locations, log_file=log_file)
    
    try:
        schema = get_tree_schema(cctree['children']) # Hierarchical Information
        if len(retrieved_text) > 0:
            bbox_list = [bbox for location in retrieved_bbox.values() for bbox in location]
            if True: # or -1 in page_list and position_vector == [-1, -1]:
                retrieved_image = bbox_to_base64(source_path, bbox_list) # Cropped regions spliced vertically
                answer = retrieved_reason(query, retrieved_text, retrieved_image, schema)
            else:
                retrieved_image = bbox_to_base64_2(source_path, bbox_list) # Cropped regions spliced by relative location relations
                answer = retrieved_reason(query, retrieved_text, retrieved_image, schema)
        else:
            answer = "None"
    except Exception as e:
        print(f"Errors in qa：{e}")
        answer = "None"

    if log_file is not None:    # Log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(
                f"{DELIMITER} Retrieved Data  {DELIMITER}\n"
            )
            f.write(f"{retrieved_text}\n")

            f.write(
                f"{DELIMITER} Answer {DELIMITER}\n"
            )
            f.write(f"{answer}\n")
    
    # Check if evidence is found
    final_check = check_answer(query=query, answer=answer)
    if log_file is not None:    # Log
        with open(log_file, 'a', encoding="utf-8") as f:
            f.write(f"{DELIMITER} Final Check for Query {DELIMITER}\n")
            f.write(f"{final_check}\n")
    
    if final_check:
        final_answer = answer
        if log_file is not None:    # Log
            with open(log_file, 'a', encoding="utf-8") as f:
                f.write(f"{DELIMITER} Final Check Passed and Final Answer{DELIMITER}\n")
                f.write(f"{final_answer}\n")
    else:
        # Answer based on whole doucment if evidence not found
        whole_doc = pdf_to_base64(source_path)
        simplify_tree(cctree['children']) 
        final_answer = whole_reason(whole_doc, query, cctree)
        if log_file is not None:    # Log
            with open(log_file, 'a', encoding="utf-8") as f:
                f.write(f"{DELIMITER} Final Answer for Whole Table Reasoning {DELIMITER}\n")
                f.write(f"{final_answer}\n")

    return final_answer