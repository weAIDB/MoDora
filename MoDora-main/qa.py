import re
import ast
import json
import traceback
from api_utils import *
from prompt_template import *
from constants import *
from logger import logger
from retrieve import *
from concurrent.futures import ThreadPoolExecutor, as_completed

def merge_multi_docs(source_paths_map):
    """
    Merge multiple document trees into a single tree.
    Args:
        source_paths_map: dict {filename: absolute_path}
    """
    root = {
        'type': 'MROOT',
        'metadata': 'Multi-document root',
        'data': 'Multi-document root',
        'location': [],
        'children': {}
    }
    
    for filename, path in source_paths_map.items():
        # Assuming cache follows the standard naming convention
        # Logic matches main.py: CACHE_DIR / dataset_name / doc_name / tree.json
        doc_cache_name = os.path.splitext(os.path.basename(path))[0]
        cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
        tree_path = os.path.join(cache_base, doc_cache_name, "tree.json")
        
        try:
            if os.path.exists(tree_path):
                with open(tree_path, 'r', encoding='utf-8') as f:
                    cctree = json.load(f)
                    # Inject source_path into the document root
                    cctree['source_path'] = path
                    
                    # Ensure document root has metadata (summary)
                    if not cctree.get('metadata'):
                        # 尝试从 children 聚合 metadata
                        children_meta = [child.get('metadata', '') for child in cctree.get('children', {}).values()]
                        # 过滤掉空的
                        children_meta = [m for m in children_meta if m]
                        
                        if children_meta:
                            # 简单截取前几个作为摘要，或者调用 integrate_metadata (需要 import cctree)
                            # 为了避免循环引用，我们这里简单拼接
                            cctree['metadata'] = "; ".join(children_meta[:5])
                        else:
                             cctree['metadata'] = f"Document: {filename}"
                    
                    root['children'][filename] = cctree
            else:
                logger.warning(f"Warning: Tree cache not found for {filename} at {tree_path}")
        except Exception as e:
            logger.error(f"Failed to load tree for {filename}: {e}")
            
    return root

def call_gpt_wrapper(prompt, config=None):
    if config:
        return gpt_generate(
            prompt, 
            key=config.get('apiKey') or API_KEY, 
            url=config.get('baseUrl') or API_URL, 
            base_model=config.get('qaModel') or MODEL
        )
    return gpt_generate(prompt)

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

def whole_reason(whole_doc, query, cctree, config=None):
    prompt = whole_reasoning_prompt.format(query=query,data=cctree)
    res = call_gpt_wrapper(prompt, config)
    return res

def retrieved_reason(query, retrieved_text, retrieved_image, schema, config=None):
    prompt = retrieved_reasoning_prompt.format(query=query, evidence=retrieved_text, schema=schema)
    res = call_gpt_wrapper(prompt, config)
    return res

def check_answer(query, answer, config=None):
    prompt = check_answer_prompt.format(query=query, answer=answer)
    res = call_gpt_wrapper(prompt, config)
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
        
    except (json.JSONDecodeError, ValueError, SyntaxError) as e:
        logger.error(f"JSON解析错误: {e}")
        logger.error(f"原始location字符串: {location_str}")
        return {'location': [], 'content': ''}
    except Exception as e:
        logger.error(f"解析响应时出错: {e}")
        return {'location': [{'page':0, 'grids':[]}], 'content': ''}

def question_parsing(question, config=None):
    prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", question)
    res = call_gpt_wrapper(prompt, config)
    return parse_response(res)

def qa(cctree, query, log_file=None, source_path=False, config=None):

    if log_file is not None:
        log_file.info(f"{DELIMITER} Answering Query {DELIMITER}\n{query}\n")

    answer = "None"
    
    # 1. 准备两套数据容器
    full_evidence = []    # 给 LLM 用 (全量)
    full_locations = []   

    display_evidence = [] # 给前端用 (Top 3 Distinct Pages)
    display_locations = []

    parsed_res = question_parsing(query, config=config)
    locations = parsed_res.get('location', [])
    semantic_query = parsed_res.get('content', query)

    if log_file is not None:
        log_file.info(f"{DELIMITER} Location Cues {DELIMITER}\n{locations}\n")
        log_file.info(f"{DELIMITER} Semantic Cues {DELIMITER}\n{semantic_query}\n")

    # 执行检索
    retrieved_text_dict, retrieved_bbox_dict = retrieve(
        query=semantic_query, 
        cctree=cctree, 
        source_path=source_path, 
        locations=locations, 
        log_file=log_file,
        config=config
    )
    
    # 2. 填充全量推理数据
    if retrieved_text_dict:
        full_evidence = list(retrieved_text_dict.values())
    if retrieved_bbox_dict:
        for bbox_list in retrieved_bbox_dict.values():
            if isinstance(bbox_list, list):
                full_locations.extend(bbox_list)

    # --- 3. [修改] 严格按页去重筛选展示数据 ---
    seen_pages = set()
    MAX_PAGES = 3
    
    # 新的存放容器
    display_documents = [] 
    
    for path, bbox_list in retrieved_bbox_dict.items():
        # Handle nodes without location (e.g. user-added nodes)
        current_page = 0
        if bbox_list:
            current_page = bbox_list[0].get('page')
        
        # 逻辑：严格按页去重
        if current_page in seen_pages:
            continue
            
        if len(seen_pages) < MAX_PAGES:
            seen_pages.add(current_page)
            
            # Determine file name
            fname = None
            if bbox_list and 'source_path' in bbox_list[0]:
                fname = os.path.basename(bbox_list[0]['source_path'])
            elif source_path:
                fname = os.path.basename(source_path)

            # 【关键修改】构造一个完整的对象，而不是拆分到两个列表
            doc_item = {
                "page": current_page,
                "content": retrieved_text_dict.get(path, ""),
                "bboxes": bbox_list,  # 这里放的是这个段落对应的 [box1, box2...]
                "file_name": fname
            }
            display_documents.append(doc_item)

    # 4. 执行推理 (使用全量数据 full_evidence)
    try:
        if 'children' in cctree:
             schema = get_tree_schema(cctree['children']) 
        else:
             schema = {}

        if len(full_evidence) > 0:
            # 修改：不再生成/使用图片进行推理，仅使用文本证据
            # retrieved_image = bbox_to_base64(source_path, full_locations)
            # 传入空图片占位，retrieved_reason 实际上只使用 prompt (文本)
            answer = retrieved_reason(semantic_query, full_evidence, None, schema, config=config)
        else:
            answer = "None"
            
    except Exception as e:
        logger.error(f"Errors in qa reasoning：{e}")
        logger.error(traceback.format_exc())
        answer = "None"

    if log_file is not None:
        log_file.info(f"{DELIMITER} Answer {DELIMITER}\n{answer}\n")
    
    # 5. 最终校验
    final_check = check_answer(query=semantic_query, answer=answer, config=config)
    
    final_answer = answer
    if not final_check:
        # 这里的 whole_doc 仍然保留，用于全文档兜底推理 (whole_reason 可能会用到)
        # whole_reason 内部使用的是 whole_reasoning_prompt (纯文本)
        # 这里的 pdf_to_base64 其实也是多余的，whole_reason 签名是 (whole_doc, query, cctree)
        # 检查 whole_reason 实现: prompt = whole_reasoning_prompt.format(query=query,data=cctree)
        # 并没有用到 whole_doc (pdf图片)。
        
        whole_doc = None
        if source_path:
            whole_doc = pdf_to_base64(source_path) 
            
        if 'children' in cctree:
            simplify_tree(cctree['children']) 
        final_answer = whole_reason(whole_doc, semantic_query, cctree, config)

    # 6. 返回结果
    return {
        "answer": final_answer,
        # "retrieved_image": retrieved_image, # 移除: 不再返回溯源图片
        # 这是一个列表，长度严格为 3

        # 前端遍历这个列表：
        #   - item.content 用于显示文字
        #   - item.page 用于跳转
        #   - item.bboxes 用于在 PDF 上画高亮 (可能有多个框)
        "retrieved_documents": display_documents 
    }