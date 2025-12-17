import re
import ast
import json
from api_utils import *
from prompt_template import *
from constants import *
from retrieve import *
from concurrent.futures import ThreadPoolExecutor, as_completed

def call_gpt_wrapper(prompt, config=None):
    if config:
        # 如果是本地模型，且在 constants.py 中我们知道本地模型不需要 API Key
        # 但这里 api_utils.py 的 gpt_generate 已经适配了 OpenAI 格式
        # 如果 config['qaModel'] 是 'qwen-vl-local'，我们需要特殊处理吗？
        # 不需要，因为我们已经在 api_utils.py 中移除了 call_qwen_*
        # 等等，如果用户选了 'qwen-vl-local'，我们应该如何处理？
        # 目前 api_utils.py 的 gpt_generate 是纯 OpenAI 调用。
        # 如果要支持本地模型，我们需要在 api_utils.py 中恢复 call_qwen_* 的能力，或者让本地模型也提供 OpenAI 兼容接口。
        # 考虑到之前的修改，api_utils.py 已经删除了 call_qwen_* 的引用。
        # 这是一个关键点！
        
        # 临时方案：如果 model 是 qwen-vl-local，我们假设它不可用或者抛错，
        # 或者我们需要恢复 api_utils.py 的本地调用能力。
        # 鉴于用户要求“保留gemini和gpt”，且“默认是本地Qwen”，
        # 这意味着我们需要支持双模式：OpenAI API 和 本地 Qwen。
        
        # 让我们先按照 OpenAI 格式传参。如果用户选了本地 Qwen，
        # 我们需要在 api_utils.py 中做判断。
        
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
        
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print(f"原始location字符串: {location_str}")
        return {'location': [], 'content': ''}
    except Exception as e:
        print(f"解析响应时出错: {e}")
        return {'location': [{'page':0, 'grids':[]}], 'content': ''}

def question_parsing(question, config=None):
    prompt = question_parsing_prompt.replace("__QUESTION_PLACEHOLDER__", question)
    res = call_gpt_wrapper(prompt, config)
    return parse_response(res)

def qa(cctree, query, log_file=None, source_path=False, config=None):

    if log_file is not None:
        with open(log_file, "a") as f:
            f.write(f"{DELIMITER} Answering Query {DELIMITER}\n{query}\n")

    answer = "None"
    
    # 1. 准备两套数据容器
    full_evidence = []    # 给 LLM 用 (全量)
    full_locations = []   

    display_evidence = [] # 给前端用 (Top 3 Distinct Pages)
    display_locations = []

    parsed_res = question_parsing(query)
    locations = parsed_res.get('location', [])
    semantic_query = parsed_res.get('content', query)

    if log_file is not None:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{DELIMITER} Location Cues {DELIMITER}\n{locations}\n")
            f.write(f"{DELIMITER} Semantic Cues {DELIMITER}\n{semantic_query}\n")

    # 执行检索
    retrieved_text_dict, retrieved_bbox_dict = retrieve(
        query=semantic_query, 
        cctree=cctree, 
        source_path=source_path, 
        locations=locations, 
        log_file=log_file
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
            
            # 【关键修改】构造一个完整的对象，而不是拆分到两个列表
            doc_item = {
                "page": current_page,
                "content": retrieved_text_dict.get(path, ""),
                "bboxes": bbox_list  # 这里放的是这个段落对应的 [box1, box2...]
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
        print(f"Errors in qa reasoning：{e}")
        import traceback
        traceback.print_exc()
        answer = "None"

    if log_file is not None:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{DELIMITER} Answer {DELIMITER}\n{answer}\n")
    
    # 5. 最终校验
    final_check = check_answer(query=semantic_query, answer=answer, config=config)
    
    final_answer = answer
    if not final_check:
        # 这里的 whole_doc 仍然保留，用于全文档兜底推理 (whole_reason 可能会用到)
        # whole_reason 内部使用的是 whole_reasoning_prompt (纯文本)
        # 这里的 pdf_to_base64 其实也是多余的，whole_reason 签名是 (whole_doc, query, cctree)
        # 检查 whole_reason 实现: prompt = whole_reasoning_prompt.format(query=query,data=cctree)
        # 并没有用到 whole_doc (pdf图片)。
        # 为了安全起见，暂时不动这个逻辑，除非确认 whole_reason 真的不用
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
        "documents": display_documents 
    }