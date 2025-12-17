import os
import numpy as np
import torch
import re
from transformers import Qwen3VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
from sentence_transformers import SentenceTransformer
from prompt_template import *
from constants import *

# 初始化模型 (Lazy Load)
qwen_vl_model = None
qwen_vl_processor = None
qwen_em_model = None

def ensure_model_loaded():
    global qwen_vl_model, qwen_vl_processor, qwen_em_model
    if qwen_vl_model is None:
        print("Loading local Qwen models...")
        qwen_vl_model = Qwen3VLForConditionalGeneration.from_pretrained(
            VL_MODEL_PATH, torch_dtype="auto", device_map="auto"
        )
        qwen_vl_processor = AutoProcessor.from_pretrained(VL_MODEL_PATH)
        
        qwen_em_model = SentenceTransformer(
            EM_MODEL_PATH, device="cpu"
        )
        print("Local Qwen models loaded.")

# qwen_vl_model = Qwen3VLForConditionalGeneration.from_pretrained(
#     VL_MODEL_PATH, torch_dtype="auto", device_map="auto"
# )
# qwen_vl_processor = AutoProcessor.from_pretrained(VL_MODEL_PATH)

# qwen_em_model = SentenceTransformer(
#     EM_MODEL_PATH, device="cpu"
# )

# --- 树结构处理工具函数 (保持不变) ---
def flat_tree(sub_tree):
    res = []
    for index, node in sub_tree.items():
        res.extend((f"{index}: {node['data']}").split("\n"))
        res.extend(flat_tree(node['children']))
    return res

def flat_tree1(key, node):
    res = merge_short_segments((key + node['data']).split("\n"))
    for index, sub_node in node['children'].items():
        res.extend(flat_tree1(index, sub_node))
    return res

def merge_short_segments(res, threshold=100):
    if not res:
        return []
    merged_res = []
    current_segment = res[0]

    for i in range(1, len(res)):
        if len(current_segment) < threshold:
            current_segment += res[i]
        else:
            merged_res.append(current_segment)
            current_segment = res[i]

    merged_res.append(current_segment)
    return merged_res

# --- 检索相关函数 (保持不变) ---
def call_qwen_em(query, sub_tree, k=3):
    queries = [query]
    documents = flat_tree1("",sub_tree)

    query_embeddings = qwen_em_model.encode(queries, prompt_name="query")
    document_embeddings = qwen_em_model.encode(documents)

    similarity = qwen_em_model.similarity(query_embeddings, document_embeddings)
    sim_scores = similarity[0]
    sorted_indices = np.argsort(-sim_scores)

    top_sentences = []
    for i in sorted_indices[:k]:
        if i < len(documents):
            top_sentences.append(documents[i])
    return " ".join(top_sentences)

# --- [重点修改] 纯文本调用函数 ---
def call_qwen_vl_textonly(prompt):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ],
        }
    ]

    # 修改：使用 tokenizer 调用，且只保留 text 相关的参数
    text = qwen_vl_processor.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # 这里的输入没有图片，所以 process_vision_info 返回的可能是 None 或空，
    # 但 qwen_vl_processor 能处理这种情况
    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = qwen_vl_processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(qwen_vl_model.device)

    generated_ids = qwen_vl_model.generate(**inputs, max_new_tokens=2048)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = qwen_vl_processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text[0]

# --- [重点修改] 带图调用函数 ---
def call_qwen_vl(prompt, base64_image):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": f"data:image/jpeg;base64,{base64_image}"},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    # 修改 1：使用 .tokenizer.apply_chat_template
    # 修改 2：删除了 return_dict=True 和 return_tensors="pt"，确保返回纯字符串
    text = qwen_vl_processor.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = qwen_vl_processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(qwen_vl_model.device)

    generated_ids = qwen_vl_model.generate(**inputs, max_new_tokens=2048)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = qwen_vl_processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text[0]

# --- 标注函数 (保持不变) ---
def qwen_annotation(base64_image, cp_type, config=None):
    from api_utils import gpt_generate_pdf
    prompt_map = {
        "table": table_enrichment_prompt,
        "chart": chart_enrichment_prompt, 
        "image": image_enrichment_prompt
    }
    prompt = prompt_map.get(cp_type, image_enrichment_prompt)

    flag = False
    cnt = 0
    pattern = r'\[T\](.*?)\[M\](.*?)\[C\](.*)'
    title = "Default Title"
    metadata = "Default Metadata"
    content = "Default Content"
    
    while not flag and cnt<3:
        # Redirect call to Gemini via api_utils
        # Use treeModel as the default for enrichment if not specified, or fallback to MODEL
        # Enrichment is part of tree construction/preprocessing
        base_model = config.get('treeModel') if config else MODEL
        
        text = gpt_generate_pdf(
            base64_image, prompt,
            key=config.get('apiKey') or API_KEY,
            url=config.get('baseUrl') or API_URL,
            base_model=base_model
        )
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            title = match.group(1).strip()
            metadata = match.group(2).strip()
            content = match.group(3).strip()
            flag = True
        else:
            cnt = cnt + 1
            print(f"Fail to parse Qwen-VL output. The output is {text}. Try for time {cnt}！")

    return title, metadata, content