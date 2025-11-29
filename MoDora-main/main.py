import os
import json
import uuid
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 引入你的后端核心模块
from qa import qa
from constants import BASE_DIR, CACHE_DIR, LOG_DIR

app = FastAPI(title="MoDora Chat API")

# --- 1. CORS 配置 (允许 Vue 前端访问) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源，生产环境建议改为 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 数据模型定义 ---
class ChatRequest(BaseModel):
    file_name: str  # 例如: "1.pdf"
    query: str      # 例如: "这篇文章讲了什么？"

class ChatResponse(BaseModel):
    answer: str
    reasoning_log: Optional[str] = ""

class TreeRequest(BaseModel):
    file_name: str

class TreeResponse(BaseModel):
    elements: list  # 包含 nodes 和 edges 的混合数组

# --- 3. 核心问答接口 ---
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
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
        # 调用核心 qa 函数
        final_answer = qa(
            cctree=cctree, 
            query=query, 
            log_file=log_file, 
            source_path=source_path
        )
        
        # 读取日志内容返回给前端 (可选)
        log_content = ""
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()
            # 调试完成后可以取消注释下面这行来自动删除日志
            # os.remove(log_file)

        return ChatResponse(
            answer=final_answer,
            reasoning_log=log_content
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

    def traverse(node, key_label, depth, parent_id):
        nonlocal leaf_counter
        
        current_id = str(uuid.uuid4())
        
        # 1. 递归处理所有子节点
        children_ids = []
        
        # cctree 的 children 是个字典，key 是标题，value 是节点对象
        children_dict = node.get('children', {})
        
        # 递归遍历子节点
        for child_key, child_node in children_dict.items():
            child_id = traverse(child_node, child_key, depth + 1, current_id)
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
            # 注意：这里需要先在 nodes 列表里找到对应子节点的 x 坐标
            # 为了简化，我们假设刚生成的 children_ids 对应的节点还在内存热区，或者我们简单存一下
            # 由于递归是深度优先，我们需要一种方式获取子节点位置。
            # 简单策略：我们先不回溯查找，直接由子节点决定父节点位置稍显麻烦。
            # 修正策略：采用后序遍历（Post-order），子节点先定好位，父节点居中。
            
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
                "id": current_id # 方便前端回调
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
    traverse(cctree, root_label, 0, None)
    
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