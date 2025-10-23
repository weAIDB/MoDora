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

def extract_location_cues(query):
    prompt = location_extraction_prompt.format(query=query)
    res = gpt_generate(prompt)
    return res

def qa(cctree, query, log_file=None, source_path=False):

    if log_file is not None:    # Log
        with open(log_file, "a") as f:
            f.write(
                f"{DELIMITER} Answering Query {DELIMITER}\n"
            )
            f.write(f"{query}\n")

    answer = "None"
    
    # Extract location cues
    location_cues = extract_location_cues(query)
    if log_file is not None:    # Log
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(
                    f"{DELIMITER} Location Cues {DELIMITER}\n"
                )
                f.write(f"{location_cues}\n")
    try:
        page_numbers = location_cues.split("Page:")[1].split(";")[0].strip()
        position = location_cues.split("Position:")[1].strip()
        page_list = ast.literal_eval(page_numbers)
        position_vector = ast.literal_eval(position)
    except Exception as e:
        print(f"Error parsing location: {e}")
        print(f"Response: {location_cues}")
        page_list = [-1]
        position_vector == [-1, -1]
    
    # Semantics-based retrival for no explict location cues
    if -1 in page_list and position_vector == [-1, -1]:
        retrieved_text, retrieved_bbox = retrieve_by_semantics(query=query,cctree=cctree,source_path=source_path,log_file=log_file)

    # Location-based retrival
    else:
        retrieved_text, retrieved_bbox = retrieve_by_location(tree=cctree['children'], page_list=page_list, position_vector=position_vector, pdf_path=source_path)

    try:
        schema = get_tree_schema(cctree['children']) # Hierarchical Information
        if len(retrieved_text) > 0:
            bbox_list = [bbox for location in retrieved_bbox.values() for bbox in location]
            if -1 in page_list and position_vector == [-1, -1]:
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