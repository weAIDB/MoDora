import os
import re
import json
import math
from logger import logger
from statistics import pvariance, mean # 总体方差


def _classify_label(label: str) -> str:
    if label is None:
        return 'text'
    s = str(label).strip().lower()
    if s == 'chart':
        return 'chart'
    if s == 'image':
        return 'image'
    if s == 'table':
        return 'table'
    if s in {'header', 'footer', 'aside', 'number'}:
        return 'layout_misc'
    return 'text'


def get_components(cache_path):
    bbox_list = []

    files = os.listdir(cache_path)
    pattern = re.compile(r'^(.+)_(\d+)_res\.json$')
    matching_files = [filename for filename in files if pattern.match(filename)]
    matching_files = sorted(matching_files, key=lambda x: int(pattern.match(x).group(2)))

    for file in matching_files:
        with open(os.path.join(cache_path, file), 'r', encoding='utf-8') as f:
            page = json.load(f)
        
        for bbox in page['parsing_res_list']:
            bbox_list.append(bbox)

    counts = {
        'chart': 0,
        'image': 0,
        'table': 0,
        'layout_misc': 0,  # header/footer/aside/number
        'text': 0 # paragraph/title
    }
    
    # 统计各主要类型元素数量
    for bbox in bbox_list:
        label = bbox.get('block_label')
        cat = _classify_label(label)
        counts[cat] += 1

    # 计算按类型统计的方差
    values = list(counts.values())
    variance = pvariance(values) if len(values) > 1 else 0.0
    try:
        variance = math.sqrt(variance) / sum(list(counts.values()))
    except Exception as e:
        variance = 0

    return counts, variance, len(matching_files)
    

def get_trees(cache_path):
    tree_path = os.path.join(cache_path, "tree.json")
    with open(tree_path, "r", encoding='utf-8') as f:
        tree = json.load(f)
    node_cnt = 0
    leaf = 0

    def traverse_and_extract(node_dict):
        nonlocal node_cnt 
        nonlocal leaf
        deep = 0
        for node_key, node_value in list(node_dict.items()):
            
            node_cnt += 1

            if "children" in node_value:
                if node_value["children"]:
                    c_deep = traverse_and_extract(node_value["children"])
                    if c_deep > deep and node_key != "Supplement":
                        deep = c_deep
                else:
                    leaf += 1

        return deep+1
    
    deep = traverse_and_extract(tree)

    return node_cnt, leaf, deep+1


def count_all(source_root):
    """
    遍历 source_root 下所有PDF对应的处理结果，统计各类潜在价值信息。
    """
    subdirs = [os.path.join(source_root, d) for d in os.listdir(source_root)]
    total_dirs = len(subdirs)
    elem_counts = []
    elem_vars = []
    page_counts = []
    node_counts = []
    leaf_counts = []
    deeps = []
    zero_dirs = 0

    for sub in subdirs:
        counts, var, page_count = get_components(sub)
        if counts.get("chart", 0) == 0 and counts.get("image", 0) == 0 and counts.get("table", 0) == 0:
            zero_dirs += 1
        elem_counts.append(counts)
        elem_vars.append(var)
        page_counts.append(page_count)

        nodes, leaves, deep = get_trees(sub)
        node_counts.append(nodes)
        leaf_counts.append(leaves)
        deeps.append(deep)

    # 计算平均数量
    avg_counts = {}
    keys = ['chart', 'image', 'table', 'layout_misc', 'text']
    for k in keys:
        avg_counts[k] = mean([c[k] for c in elem_counts]) if elem_counts else 0.0

    avg_var = mean(elem_vars) if elem_vars else 0.0
    avg_pages = mean(page_counts)
    avg_nodes = mean(node_counts)
    avg_leaves = mean(leaf_counts)
    avg_deep = mean(deeps)
    zero_ratio = zero_dirs/total_dirs
    

    logger.info("\n===== 汇总统计结果 =====")
    logger.info(f"平均文档页数: {avg_pages:.2f}")
    for k, v in avg_counts.items():
        logger.info(f"{k:12s}: 平均元素数量 = {v:.2f}")
    logger.info(f"平均元素标准差: {avg_var:.4f}")
    logger.info(f"平均树节点数: {avg_nodes:.2f}")
    logger.info(f"平均叶节点数: {avg_leaves:.2f}")
    logger.info(f"平均树最大深度: {avg_deep:.2f}")
    logger.info(f"单调文档: {zero_dirs}/{total_dirs} ({zero_ratio:.2f}%)")

    return avg_counts, avg_var
