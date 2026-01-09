import os
import json
import uuid
import uvicorn
from typing import Optional, List, Dict, Any, Union
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import shutil
from fastapi import UploadFile, File, BackgroundTasks, Form
from preprocess import preprocess
from cctree import build_tree
from stati import get_components, get_trees
from kb_manager import kb_manager
from logger import logger, modora_logger

# 引入你的后端核心模块
from qa import qa
from constants import BASE_DIR, CACHE_DIR, LOG_DIR

app = FastAPI(title="MoDora Chat API")

@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Duration: {duration:.2f}s")
    return response

app.mount("/api/files", StaticFiles(directory=BASE_DIR), name="files")

# --- 1. CORS 配置 (允许 Vue 前端访问) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源，生产环境建议改为 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 数据模型定义 ---
import io
import fitz
from fastapi.responses import StreamingResponse

@app.get("/api/pdf/{file_name}/{page_index}/image")
def get_pdf_image(file_name: str, page_index: int):
    source_path = os.path.join(BASE_DIR, file_name)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        doc = fitz.open(source_path)
        if page_index < 1 or page_index > len(doc):
            doc.close()
            raise HTTPException(status_code=400, detail="Invalid page index")

        page = doc[page_index - 1]
        # 使用较高的 DPI 渲染以保证清晰度 (zoom=2.0 相当于 144 DPI)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_data = pix.tobytes("png")
        doc.close()
        
        return StreamingResponse(io.BytesIO(img_data), media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating PDF image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    file_name: Optional[str] = None  # 单文件兼容
    file_names: Optional[List[str]] = None # 多文件支持
    query: str      # 例如: "这篇文章讲了什么？"
    settings: Optional[Dict] = None # 前端传来的配置

class RetrievalItem(BaseModel):
    page: int
    content: str
    bboxes: List[Any]  # 这一项对应的所有高亮框
    score: Optional[float] = 0.0
    file_name: Optional[str] = None # 所属文件名

class ChatResponse(BaseModel):
    answer: str
    reasoning_log: Optional[str] = ""
    # retrieved_image: Optional[str] = ""  # 移除
    # 废弃原来的分离字段，改用结构化列表
    retrieved_documents: List[RetrievalItem] = []
    node_impacts: Dict[str, int] = {}

class TreeRequest(BaseModel):
    file_name: str

class TreeResponse(BaseModel):
    elements: list  # 包含 nodes 和 edges 的混合数组

class TreeUpdateRequest(BaseModel):
    file_name: str
    elements: list  # Vue Flow 的 elements (nodes 和 edges)

class DocStatsResponse(BaseModel):
    pages: int
    counts: Dict[str, int]
    variance: float
    nodes: int
    leaves: int
    depth: int
    tags: List[str] = []
    semantic_tags: List[str] = []

class SessionStatsRequest(BaseModel):
    file_names: List[str]

class SessionStatsResponse(BaseModel):
    total_files: int
    avg_pages: float
    avg_nodes: float
    avg_depth: float
    total_counts: Dict[str, int]
    avg_variance: float

class UpdateTagsRequest(BaseModel):
    file_name: str
    tags: List[str]

def reconstruct_tree_from_elements(elements, original_tree, file_name):
    """
    根据 Vue Flow 的 elements 重构 tree.json 结构
    保留原有的 data/location 信息，同时应用前端的增删改
    """
    # 1. 构建原始树的路径映射表 (path_tuple -> node_dict)
    original_path_map = {}
    
    def traverse_map(node, current_path):
        original_path_map[tuple(current_path)] = node
        for title, child in node.get("children", {}).items():
            traverse_map(child, current_path + [title])
            
    # 根节点路径是 [file_name]
    traverse_map(original_tree, [file_name])
    
    # 2. 解析 elements 为图结构
    nodes = {}
    edges = []
    for el in elements:
        if 'source' in el and 'target' in el:
            edges.append(el)
        else:
            nodes[el['id']] = el
            
    adj = {nid: [] for nid in nodes}
    in_degree = {nid: 0 for nid in nodes}
    
    for e in edges:
        s, t = e['source'], e['target']
        if s in nodes and t in nodes:
            adj[s].append(t)
            in_degree[t] += 1
            
    # 3. 寻找根节点
    roots = [nid for nid, d in in_degree.items() if d == 0]
    if not roots:
        raise ValueError("No root node found in the graph (cycle or empty).")
    
    # 如果有多个根，尝试找到 label 匹配 file_name 的那个
    root_id = None
    if len(roots) == 1:
        root_id = roots[0]
    else:
        for r in roots:
            lbl = nodes[r].get('label') or nodes[r].get('data', {}).get('label')
            if lbl == file_name:
                root_id = r
                break
        if not root_id:
            # 默认取第一个
            root_id = roots[0]

    # 4. 递归重建
    def build_node(node_id):
        node = nodes[node_id]
        # 获取 Label
        label = node.get('label') or node.get('data', {}).get('label') or 'Untitled'
        
        # 尝试查找原始数据
        original_path = node.get('data', {}).get('path')
        found_orig = False
        
        node_data = {}
        
        # 1. 优先使用前端传回的编辑后的数据 (data 字段)
        frontend_data = node.get('data', {})
        
        node_data["type"] = frontend_data.get("type", "text")
        node_data["metadata"] = frontend_data.get("metadata", "")
        node_data["data"] = frontend_data.get("data", "")
        
        # 2. 如果前端没有 location，尝试从原始数据中获取 (location 通常不支持前端编辑)
        if original_path and tuple(original_path) in original_path_map:
            orig = original_path_map[tuple(original_path)]
            # 只有当 location 缺失时才回退到原始数据
            # (不过通常 location 都在 frontend_data 里，除非是新节点)
            if "location" not in frontend_data:
                 node_data["location"] = orig.get("location", [])
            else:
                 node_data["location"] = frontend_data.get("location", [])
            
            # Preserve 'impact' if it exists in original node
            if "impact" in orig:
                node_data["impact"] = orig["impact"]
        else:
            # 新节点，使用前端提供的 location，或者空列表
            node_data["location"] = frontend_data.get("location", [])
            
        # 处理子节点
        children_dict = {}
        child_ids = adj[node_id]
        # 按 X 坐标排序，保证视觉顺序一致
        child_ids.sort(key=lambda x: nodes[x].get('position', {}).get('x', 0))
        
        for cid in child_ids:
            child_label, child_obj = build_node(cid)
            # 防止重名 key
            base_label = child_label
            counter = 1
            while child_label in children_dict:
                child_label = f"{base_label} ({counter})"
                counter += 1
            children_dict[child_label] = child_obj
            
        node_data["children"] = children_dict
        return label, node_data

    # 构建
    _, new_tree_root = build_node(root_id)
    
    # 确保根节点的 type
    if "type" not in new_tree_root:
        new_tree_root["type"] = "root"
        
    return new_tree_root

def validate_tree_structure(tree):
    """
    Recursively validate the tree structure.
    Ensures that every node is a dictionary with 'type' and 'children' fields,
    and that 'children' is a dictionary.
    """
    if not isinstance(tree, dict):
        raise ValueError("Node must be a dictionary.")
    
    # Check required fields
    if "type" not in tree:
        raise ValueError("Node must have a 'type' field.")
    
    # 'children' is mandatory in our tree structure
    if "children" not in tree:
        raise ValueError("Node must have a 'children' field.")
        
    if not isinstance(tree["children"], dict):
        raise ValueError("'children' field must be a dictionary.")
        
    # Recursively check children
    for key, child in tree["children"].items():
        if not key or not isinstance(key, str):
            raise ValueError("Child key must be a non-empty string.")
        validate_tree_structure(child)

@app.post("/api/tree/update")
def update_tree_endpoint(request: TreeUpdateRequest):
    file_name = request.file_name
    elements = request.elements
    
    # 1. Path derivation
    doc_name = os.path.splitext(file_name)[0]
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    tree_path = os.path.join(cache_base, doc_name, "tree.json")
    
    if not os.path.exists(tree_path):
        raise HTTPException(status_code=404, detail=f"Tree cache not found: {tree_path}")

    try:
        # 2. Read original tree.json (to preserve data/location)
        with open(tree_path, "r", encoding="utf-8") as f:
            original_tree_dict = json.load(f)
            
        # 3. Reconstruct tree structure
        logger.info(f"Reconstructing tree for {file_name}...")
        new_tree_dict = reconstruct_tree_from_elements(elements, original_tree_dict, file_name)
        
        # 4. Validate tree structure
        logger.info("Validating tree structure...")
        validate_tree_structure(new_tree_dict)
        
        # 5. Save (Re-compile)
        logger.info(f"Saving (Re-compiling) tree to {tree_path}...")
        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(new_tree_dict, f, ensure_ascii=False, indent=4)
            
        return {"status": "success", "message": "Tree structure validated and re-compiled successfully."}

    except ValueError as ve:
        logger.error(f"Validation Error: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid tree structure: {str(ve)}")
    except Exception as e:
        logger.error(f"Compilation Error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# --- 2.7 更新树节点接口 (原子操作) ---
class NodeUpdate(BaseModel):
    file_name: str
    action: str  # "update", "delete", "add"
    target_path: List[str]  # 目标节点的路径 (标题列表，从根节点开始)
    new_data: Optional[Dict] = None # 用于 update/add 的数据

@app.post("/api/tree/node/update")
def update_node_endpoint(request: NodeUpdate):
    from tree_structure import dict_to_tree, TreeNode
    
    file_name = request.file_name
    
    doc_name = os.path.splitext(file_name)[0]
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    tree_path = os.path.join(cache_base, doc_name, "tree.json")
    
    if not os.path.exists(tree_path):
        raise HTTPException(status_code=404, detail="Tree not found")

    # 1. 加载并重建对象树
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            tree_dict = json.load(f)
        
        # 修正：将 root_title 设置为 file_name，以便与前端展示一致
        # 前端展示时，根节点标题通常是 file_name
        root = dict_to_tree(tree_dict, root_title=file_name)
        
        # 2. 找到目标节点
        # 重写路径查找逻辑，更灵活
        current_node = root
        parent_node = None
        
        # 1. 检查路径起点
        actual_search_path = request.target_path
        
        # 策略：如果路径的第一个元素是根节点（无论是文件名还是 "Document Root"），就跳过它
        if actual_search_path:
            first_segment = actual_search_path[0]
            # 如果第一个分段匹配当前的根节点标题，或者它是默认的 "Document Root"，我们认为它是根，跳过
            if first_segment == root.title or first_segment == "Document Root":
                actual_search_path = actual_search_path[1:]
            
            pass

        for i, title in enumerate(actual_search_path):
            parent_node = current_node
            found = current_node.find_child(title)
            
            if not found:
                # 特殊情况：如果是路径的第一个元素，且它没在子节点里找到
                # 只有当它是路径的第一个元素时才尝试跳过
                if i == 0:
                     # 检查下一个元素是否是 root 的子节点
                     if len(actual_search_path) > 1:
                         next_title = actual_search_path[1]
                         if current_node.find_child(next_title):
                             continue
                
                # 真的找不到了
                available = []
                if parent_node:
                    available = [c.title for c in parent_node.children]
                elif current_node:
                     available = [c.title for c in current_node.children]
                
                raise HTTPException(status_code=404, detail=f"Node not found: '{title}' in path {request.target_path}. Available children: {available}")
            
            current_node = found
        
        # 3. 执行操作
        if request.action == "update":
            if request.new_data:
                if "title" in request.new_data:
                    current_node.title = request.new_data["title"]
                if "data" in request.new_data:
                    current_node.data = request.new_data["data"]
                # 可以添加更多字段的更新
                
        elif request.action == "delete":
            if parent_node:
                parent_node.delete_child(current_node)
            else:
                raise HTTPException(status_code=400, detail="Cannot delete root node")
                
        elif request.action == "add":
            if request.new_data:
                new_child = TreeNode(
                    title=request.new_data.get("title", "New Node"),
                    typ=request.new_data.get("type", "text"),
                    data=request.new_data.get("data", "")
                )
                current_node.insert_child(new_child)
                
        # 4. 保存回 JSON
        new_tree_dict = root.to_dict()
        
        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(new_tree_dict, f, ensure_ascii=False, indent=4)
            
        return {"status": "success", "message": f"Node {request.action}d successfully"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 2.5 上传与处理接口 ---
# 简单的内存任务状态存储
# key: filename, value: status ("processing", "completed", "failed")
task_status_store = {}

from datetime import datetime

def generate_auto_tags(file_path: str, cache_base: str):
    """
    根据统计数据自动生成标签
    """
    doc_name = os.path.splitext(os.path.basename(file_path))[0]
    cache_path = os.path.join(cache_base, doc_name)
    
    tags = []
    try:
        counts, variance, page_count = get_components(cache_path)
        nodes, leaves, depth = get_trees(cache_path)
        
        # 1. 尺寸类
        if page_count > 20: tags.append("Long")
        elif page_count > 5: tags.append("Medium")
        else: tags.append("Short")
        
        # 2. 内容类
        if counts.get('table', 0) > 3: tags.append("Table-Rich")
        if counts.get('chart', 0) > 3: tags.append("Chart-Rich")
        if counts.get('image', 0) > 5: tags.append("Image-Rich")
        
        # 3. 结构类
        if variance > 0.5: tags.append("Complex Layout")
        if depth > 5: tags.append("Deep Hierarchy")
        
    except Exception as e:
        logger.error(f"Error generating auto tags: {e}")
        return []

def generate_semantic_tags(file_path: str, cache_base: str, config: Optional[Dict] = None):
    """
    调用 LLM 生成语义标签 (预留接口)
    """
    # 这里可以读取 cp.json 的前几个文本块，调用 LLM 总结
    # 暂时返回一些通用占位符，模拟 LLM 行为
    return ["Automated Analysis"]

def process_document_task(file_path: str, config: Optional[Dict] = None):
    """
    后台任务：对上传的文件进行预处理和树构建
    """
    filename = os.path.basename(file_path)
    try:
        task_status_store[filename] = "processing"
        
        # 确保缓存目录存在
        cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
        if not os.path.exists(cache_base):
            os.makedirs(cache_base)
            
        logger.info(f"后台任务开始: 处理文件 {file_path}")
        
        # 1. 预处理
        preprocess(file_path, cache_base, config=config)
        
        # 2. 构建层级树
        build_tree(file_path, cache_base, config=config)
        
        # 3. 自动生成标签并更新知识库
        auto_tags = generate_auto_tags(file_path, cache_base)
        semantic_tags = generate_semantic_tags(file_path, cache_base, config)
        
        kb_manager.update_doc_info(filename, {
            "tags": auto_tags,
            "semantic_tags": semantic_tags,
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        logger.info(f"后台任务完成: {file_path}, 自动标签: {auto_tags}")
        task_status_store[filename] = "completed"
        
    except Exception as e:
        logger.error(f"后台任务出错: {file_path}, 错误: {str(e)}")
        logger.error(traceback.format_exc())
        task_status_store[filename] = "failed"

@app.get("/api/task/status/{filename}")
def get_task_status(filename: str):
    status = task_status_store.get(filename, "unknown")
    
    # 如果是 unknown，检查一下是否已经有 tree.json 存在，如果存在也视为 completed
    # 这种情况适用于服务重启后内存丢失，但文件其实已经处理好的情况
    if status == "unknown":
        doc_name = os.path.splitext(filename)[0]
        cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
        tree_path = os.path.join(cache_base, doc_name, "tree.json")
        if os.path.exists(tree_path):
            return {"status": "completed"}
            
    return {"status": status}

from fastapi import UploadFile, File, BackgroundTasks, Form

@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    settings: Optional[str] = Form(None)
):
    # 解析 settings
    config = None
    if settings:
        try:
            config = json.loads(settings)
            logger.info(f"Upload received settings: {config}")
        except json.JSONDecodeError:
            logger.warning("Failed to parse settings JSON")
            config = {}

    # 确保保存目录存在
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
        
    file_location = os.path.join(BASE_DIR, file.filename)
    
    # 保存文件
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
        
    # 初始化状态
    task_status_store[file.filename] = "pending"
    
    # 添加后台处理任务
    background_tasks.add_task(process_document_task, file_location, config=config)
    
    return {
        "filename": file.filename, 
        "status": "uploaded", 
        "message": "文件上传成功，正在后台进行预处理，请稍候提问。"
    }

# --- 2.8 知识库与标签管理接口 ---

@app.get("/api/kb/docs")
def get_kb_docs():
    """获取知识库中的所有文档及其元数据"""
    return kb_manager.get_all_docs()

@app.get("/api/kb/tags")
def get_kb_tags():
    """获取全局标签库"""
    return kb_manager.get_tag_library()

@app.post("/api/kb/doc/tags")
def update_kb_doc_tags(request: UpdateTagsRequest):
    """更新文档的标签"""
    kb_manager.update_doc_tags(request.file_name, request.tags)
    return {"status": "success"}

@app.delete("/api/kb/tag/{tag}")
def delete_kb_tag(tag: str):
    """从全局库中删除标签"""
    kb_manager.delete_tag_from_library(tag)
    return {"status": "success"}

# --- 3. 核心问答接口 ---
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    file_names = request.file_names
    # Fallback to single file_name if file_names is missing
    if not file_names and request.file_name:
        file_names = [request.file_name]
    
    if not file_names:
        raise HTTPException(status_code=400, detail="File name(s) required")

    logger.info(f"收到请求 -> 文件: {file_names}, 问题: {request.query}")

    # 1. 准备 source_paths_map 和 source_path (兼容单文件)
    source_paths_map = {}
    for fname in file_names:
        s_path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(s_path):
             raise HTTPException(status_code=404, detail=f"File not found: {fname}")
        source_paths_map[fname] = s_path

    # 2. 获取 cctree
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    
    qa_source_path = None
    cctree = None

    if len(file_names) == 1:
        # 单文件模式：保持原有逻辑
        single_fname = file_names[0]
        qa_source_path = source_paths_map[single_fname]
        doc_name = os.path.splitext(single_fname)[0]
        tree_path = os.path.join(cache_base, doc_name, "tree.json")
        
        if not os.path.exists(tree_path):
             raise HTTPException(status_code=404, detail=f"Tree cache not found for {single_fname}. Please wait for processing.")
        
        try:
            with open(tree_path, "r", encoding="utf-8") as f:
                cctree = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load tree: {e}")
            
    else:
        # 多文件模式
        from qa import merge_multi_docs 
        cctree = merge_multi_docs(source_paths_map)
        # qa_source_path 保持为 None，因为路径在 cctree 节点里

    # 3. 执行 QA
    req_id = str(uuid.uuid4())[:8]
    req_logger = modora_logger.get_request_logger(req_id)
    log_file = os.path.join(LOG_DIR, f"api_req_{req_id}.log")
    
    try:
        # qa 返回 {"answer": ..., "documents": ...}
        qa_result = qa(
            cctree=cctree, 
            query=request.query, 
            log_file=req_logger, 
            source_path=qa_source_path, 
            config=request.settings
        )
        
        # 读取日志内容
        log_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()

        documents = []
         # Use the correct key from qa result
        for doc in qa_result.get("retrieved_documents", []):
             documents.append(RetrievalItem(
                 page=doc.get('page', 0),
                 content=doc.get('content', ""),
                 bboxes=doc.get('bboxes', []),
                 file_name=doc.get('file_name')
             ))
            
        return ChatResponse(
            answer=qa_result.get("answer", "No answer"),
            reasoning_log=log_content,
            retrieved_documents=documents,
            node_impacts=qa_result.get("node_impacts", {})
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"QA process failed: {str(e)}")

def convert_tree_to_vueflow(cctree, root_label="Document Root"):
    nodes = []
    edges = []
    
    # 布局参数
    Y_GAP = 150  # 层级之间的垂直距离
    X_GAP = 220  # 节点之间的水平距离
    
    # 用于记录当前层级下一个可用的 X 坐标（为了简单的避免重叠）
    # 实际上完美的树形布局很复杂，这里使用简化的“按叶子节点展开”算法
    leaf_counter = 0

    def traverse(node, key_label, depth, parent_id, path):
        nonlocal leaf_counter
        
        current_id = str(uuid.uuid4())
        
        # 0. 更新路径
        current_path = path + [key_label]
        
        # 1. 递归处理所有子节点
        children_ids = []
        
        # cctree 的 children 是个字典，key 是标题，value 是节点对象
        children_dict = node.get('children', {})
        
        # 递归遍历子节点
        for child_key, child_node in children_dict.items():
            child_id = traverse(child_node, child_key, depth + 1, current_id, current_path)
            children_ids.append(child_id)
            
        # 2. 计算当前节点的 X, Y 坐标
        # Y 坐标完全取决于深度
        position_y = depth * Y_GAP
        
        # X 坐标计算：
        # 如果是叶子节点，排在当前最右边
        # 如果有子节点，X 坐标等于所有子节点 X 坐标的中心
        if not children_ids:
            position_x = leaf_counter * X_GAP
            leaf_counter += 1
        else:
            # 找到第一个子节点和最后一个子节点，取中间值
            # 采用后序遍历（Post-order），子节点先定好位，父节点居中。
            
            child_nodes_x = []
            for n in nodes:
                if n['id'] in children_ids:
                    child_nodes_x.append(n['position']['x'])
            
            if child_nodes_x:
                position_x = sum(child_nodes_x) / len(child_nodes_x)
            else:
                position_x = leaf_counter * X_GAP # 兜底

        # 3. 创建 Node 对象
        node_obj = {
            "id": current_id,
            "type": "custom", # 对应前端的 <template #node-custom>
            "label": key_label, # 标题作为 Label
            "position": { "x": position_x, "y": position_y },
            "data": {
                "type": node.get('type', 'unknown'),
                "metadata": node.get('metadata', ''),
                "id": current_id, # 方便前端回调
                "path": current_path, # 传递路径给前端
                "impact": node.get('impact', 0) # 传递热力值
            }
        }
        nodes.append(node_obj)
        
        # 4. 创建 Edge 对象 (如果有父节点)
        if parent_id:
            edge_obj = {
                "id": f"e_{parent_id}_{current_id}",
                "source": parent_id,
                "target": current_id,
                "animated": True,
                "style": { "stroke": "#6366f1" }
            }
            edges.append(edge_obj)
            
        return current_id

    # 开始遍历
    traverse(cctree, root_label, 0, None, [])
    
    return nodes + edges

# 展示树结构的接口
@app.post("/api/tree", response_model=TreeResponse)
async def get_document_tree(request: TreeRequest):
    file_name = request.file_name
    
    # 1. 路径推导
    doc_name = os.path.splitext(file_name)[0]
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    tree_path = os.path.join(cache_base, doc_name, "tree.json")
    
    if not os.path.exists(tree_path):
        raise HTTPException(status_code=404, detail="Tree cache not found.")
        
    # 2. 加载数据
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            cctree = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load JSON file.")
        
    # 3. 转换格式
    elements = convert_tree_to_vueflow(cctree, root_label=file_name)
    
    return TreeResponse(elements=elements)

# --- 2.7 知识库与标签接口 ---
class TagUpdate(BaseModel):
    file_name: str
    tags: List[str]

@app.get("/api/kb/docs")
async def get_kb_docs():
    return kb_manager.get_all_docs()

@app.get("/api/kb/tags")
async def get_kb_tags():
    return kb_manager.get_tag_library()

@app.post("/api/docs/tags/update")
async def update_doc_tags(request: TagUpdate):
    kb_manager.update_doc_info(request.file_name, {"tags": request.tags})
    return {"status": "success"}

@app.post("/api/kb/tags/add")
async def add_global_tag(tag: str):
    kb_manager.add_to_tag_library(tag)
    return {"status": "success"}

@app.delete("/api/kb/tags/delete/{tag}")
async def delete_global_tag(tag: str):
    kb_manager.remove_from_tag_library(tag)
    return {"status": "success"}

# --- 2.6 统计接口 ---
@app.get("/api/docs/stats/{file_name}", response_model=DocStatsResponse)
async def get_doc_stats(file_name: str):
    doc_name = os.path.splitext(file_name)[0]
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    cache_path = os.path.join(cache_base, doc_name)
    
    if not os.path.exists(cache_path):
        raise HTTPException(status_code=404, detail=f"Stats not found for {file_name}")
        
    try:
        counts, variance, page_count = get_components(cache_path)
        nodes, leaves, depth = get_trees(cache_path)
        
        # 从知识库获取持久化的标签
        doc_info = kb_manager.get_doc_info(file_name)
        tags = doc_info.get("tags", []) if doc_info else []
        semantic_tags = doc_info.get("semantic_tags", []) if doc_info else []
        
        return DocStatsResponse(
            pages=page_count,
            counts=counts,
            variance=variance,
            nodes=nodes,
            leaves=leaves,
            depth=depth,
            tags=tags,
            semantic_tags=semantic_tags
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/stats", response_model=SessionStatsResponse)
async def get_session_stats(request: SessionStatsRequest):
    file_names = request.file_names
    if not file_names:
        return SessionStatsResponse(
            total_files=0, avg_pages=0, avg_nodes=0, avg_depth=0,
            total_counts={'chart':0, 'image':0, 'table':0, 'layout_misc':0, 'text':0},
            avg_variance=0
        )
        
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
    
    total_pages = 0
    total_nodes = 0
    total_depth = 0
    total_counts = {'chart':0, 'image':0, 'table':0, 'layout_misc':0, 'text':0}
    total_variance = 0
    valid_count = 0
    
    for file_name in file_names:
        doc_name = os.path.splitext(file_name)[0]
        cache_path = os.path.join(cache_base, doc_name)
        
        if os.path.exists(cache_path):
            try:
                counts, variance, page_count = get_components(cache_path)
                nodes, leaves, depth = get_trees(cache_path)
                
                total_pages += page_count
                total_nodes += nodes
                total_depth += depth
                total_variance += variance
                for k, v in counts.items():
                    total_counts[k] = total_counts.get(k, 0) + v
                valid_count += 1
            except:
                continue
                
    if valid_count == 0:
        raise HTTPException(status_code=404, detail="No valid stats found for session files")
        
    return SessionStatsResponse(
        total_files=valid_count,
        avg_pages=total_pages / valid_count,
        avg_nodes=total_nodes / valid_count,
        avg_depth=total_depth / valid_count,
        total_counts=total_counts,
        avg_variance=total_variance / valid_count
    )

# --- 启动入口 ---
if __name__ == "__main__":
    # Preload local models
    try:
        from qwen_call import ensure_model_loaded
        logger.info("Preloading local Qwen models...")
        ensure_model_loaded()
        logger.info("Local Qwen models preloaded successfully.")
    except Exception as e:
        logger.warning(f"Warning: Failed to preload local models: {e}")
        logger.warning("Models will be loaded lazily upon first request.")

    # 启动服务，监听 8005 端口
    logger.info("启动 FastAPI 服务...")
    logger.info(f"PDF 搜索路径: {BASE_DIR}")
    logger.info(f"Cache 搜索路径: {os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))}")
    uvicorn.run(app, host="0.0.0.0", port=8005)