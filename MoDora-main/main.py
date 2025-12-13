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
from fastapi import UploadFile, File, BackgroundTasks
from preprocess import preprocess
from cctree import build_tree

# 引入你的后端核心模块
from qa import qa
from constants import BASE_DIR, CACHE_DIR, LOG_DIR

app = FastAPI(title="MoDora Chat API")

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
        print(f"Error generating PDF image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    file_name: str  # 例如: "1.pdf"
    query: str      # 例如: "这篇文章讲了什么？"

class RetrievalItem(BaseModel):
    page: int
    content: str
    bboxes: List[Any]  # 这一项对应的所有高亮框
    score: Optional[float] = 0.0

class ChatResponse(BaseModel):
    answer: str
    reasoning_log: Optional[str] = ""
    # retrieved_image: Optional[str] = ""  # 移除
    # 废弃原来的分离字段，改用结构化列表
    retrieved_documents: List[RetrievalItem] = []

class TreeRequest(BaseModel):
    file_name: str

class TreeResponse(BaseModel):
    elements: list  # 包含 nodes 和 edges 的混合数组

class TreeUpdateRequest(BaseModel):
    file_name: str
    elements: list  # Vue Flow 的 elements (nodes 和 edges)

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
        print(f"Reconstructing tree for {file_name}...")
        new_tree_dict = reconstruct_tree_from_elements(elements, original_tree_dict, file_name)
        
        # 4. Validate tree structure
        print("Validating tree structure...")
        validate_tree_structure(new_tree_dict)
        
        # 5. Save (Re-compile)
        print(f"Saving (Re-compiling) tree to {tree_path}...")
        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(new_tree_dict, f, ensure_ascii=False, indent=4)
            
        return {"status": "success", "message": "Tree structure validated and re-compiled successfully."}

    except ValueError as ve:
        print(f"Validation Error: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"Invalid tree structure: {str(ve)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
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

def process_document_task(file_path: str):
    """
    后台任务：对上传的文件进行预处理和树构建
    """
    filename = os.path.basename(file_path)
    try:
        task_status_store[filename] = "processing"
        
        # 确保缓存目录存在
        # 注意：这里的逻辑与 pipeline.py 保持一致
        cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))
        if not os.path.exists(cache_base):
            os.makedirs(cache_base)
            
        print(f"后台任务开始: 处理文件 {file_path} -> cache: {cache_base}")
        
        # 1. 预处理 (OCR, 布局分析等)
        preprocess(file_path, cache_base)
        
        # 2. 构建层级树
        build_tree(file_path, cache_base)
        
        print(f"后台任务完成: {file_path}")
        task_status_store[filename] = "completed"
        
    except Exception as e:
        print(f"后台任务出错: {file_path}, 错误: {str(e)}")
        task_status_store[filename] = "failed"
        # 这里可以添加更复杂的错误处理，比如记录到错误日志文件

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

@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
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
    background_tasks.add_task(process_document_task, file_location)
    
    return {
        "filename": file.filename, 
        "status": "uploaded", 
        "message": "文件上传成功，正在后台进行预处理，请稍候提问。"
    }

# --- 3. 核心问答接口 ---
@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    file_name = request.file_name
    query = request.query

    print(f"收到请求 -> 文件: {file_name}, 问题: {query}")

    # --- A. 路径推导逻辑 (复用 test_qa.py 的逻辑) ---
    # 1. 源文件路径 (PDF)
    # 假设文件就在 BASE_DIR 下 (即 /datasets/MMDA/MMDA_complete/1.pdf)
    source_path = os.path.join(BASE_DIR, file_name)
    
    # 2. 缓存文件路径 (Tree JSON)
    # 逻辑: cache/MMDA_complete/1/tree.json
    doc_name = os.path.splitext(file_name)[0]  # 去掉后缀, "1.pdf" -> "1"
    cache_base = os.path.join(CACHE_DIR, os.path.basename(BASE_DIR)) # cache/MMDA_complete
    tree_path = os.path.join(cache_base, doc_name, "tree.json")

    # --- B. 校验文件是否存在 ---
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail=f"Source file not found: {source_path}")
    
    if not os.path.exists(tree_path):
        raise HTTPException(status_code=404, detail=f"Tree cache not found for: {file_name}. Please ensure pipeline has run.")

    # --- C. 加载文档树 ---
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            cctree = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load tree.json: {str(e)}")

    # --- D. 执行问答 (QA) ---
    # 创建一个临时的日志文件来捕获推理过程
    req_id = str(uuid.uuid4())[:8]
    log_file = os.path.join(LOG_DIR, f"api_req_{req_id}.log")

    try:
        qa_result = qa(
            cctree=cctree, 
            query=query, 
            log_file=log_file, 
            source_path=source_path
        )
        # ==================== 🐛 DEBUG START ====================
        print("\n" + "="*30 + " DEBUG LOG " + "="*30)
        
        # Adapt to new qa() return structure which uses 'documents' instead of 'locations'/'evidence'
        documents_debug = qa_result.get("documents", [])
        raw_locs = []
        raw_evidence = []
        
        for doc in documents_debug:
            if 'bboxes' in doc and isinstance(doc['bboxes'], list):
                raw_locs.extend(doc['bboxes'])
            if 'content' in doc:
                raw_evidence.append(doc['content'])
        
        print(f"DEBUG: 返回的位置列表长度 (Items Count): {len(raw_locs)}")
        print(f"DEBUG: 返回的证据列表长度 (Evidence Count): {len(raw_evidence)}")
        
        # 打印去重后的页码，看看实际包含了哪些页
        debug_pages = [loc.get('page') for loc in raw_locs if isinstance(loc, dict)]
        unique_debug_pages = list(set(debug_pages))
        print(f"DEBUG: 包含的所有页码 (Raw Pages): {debug_pages}")
        print(f"DEBUG: 唯一页码 (Unique Pages): {unique_debug_pages}")
        print(f"DEBUG: 唯一页码数量: {len(unique_debug_pages)}")
        
        # 检查是否真的超过3个不同页码
        if len(unique_debug_pages) > 3:
            print("❌ 错误：页码数量超过了 3 个！")
        else:
            print("✅ 正常：页码数量控制在 3 个以内。")

        # 检查是否有同一页的重复内容（如果你的需求是同一页只显示一个框）
        # 如果你发现 raw_locs 长度很大，但 unique_debug_pages 只有 3，说明同一页有很多个框
        print("="*71 + "\n")
        # ==================== 🐛 DEBUG END ====================

        # 读取日志内容
        log_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()
        
        documents = []
        for doc in qa_result.get("documents", []):
            # 直接使用树中的 bbox (2x)，因为前端展示的 PDF 图片也是 2x 的
            # 不需要再乘以 0.5，否则框会变小且位置错误
            documents.append(RetrievalItem(
                page=doc['page'],
                content=doc['content'],
                bboxes=doc.get('bboxes', [])
            ))

        return ChatResponse(
            answer=qa_result.get("answer", "No answer"),
            reasoning_log=log_content,
            # retrieved_image=qa_result.get("retrieved_image", ""),
            retrieved_documents=documents # 返回新字段
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"QA Execution Error: {str(e)}")

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
                "path": current_path # 传递路径给前端
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

# --- 启动入口 ---
if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    print("启动 FastAPI 服务...")
    print(f"PDF 搜索路径: {BASE_DIR}")
    print(f"Cache 搜索路径: {os.path.join(CACHE_DIR, os.path.basename(BASE_DIR))}")
    uvicorn.run(app, host="0.0.0.0", port=8000)