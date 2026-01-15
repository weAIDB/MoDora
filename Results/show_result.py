import json
import os
import glob

# 模型文件映射
MODEL_FILES = {
    "resudop.jsonl": "UDOP",
    "resdocowl.jsonl": "DocOwl2", 
    "resm3rag.jsonl": "M3DocRAG",
    "restxtrag.jsonl": "TextRAG",
    "ressvrag.jsonl": "SV-RAG",
    "reszendb.jsonl": "ZenDB",
    "resgpt5.jsonl": "GPT-5",
    "resquest.jsonl": "QUEST",
    "res_gpt_new.jsonl": "MoDora"
}

def show_question_results(qid):
    """显示指定questionId的所有模型结果"""
    print(f"查找问题ID: {qid}")
    print("=" * 80)
    
    found = False
    for filename, model_name in MODEL_FILES.items():
        if not os.path.exists(filename):
            continue
            
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # 尝试两种方式匹配：字符串或数字
                    if str(data.get("questionId", "")) == str(qid):
                        found = True
                        judge = data.get("judge", "F")
                        correct = "✓" if "T" in judge else "✗"
                        
                        print(f"\n{model_name}:")
                        print(f"  正确: {correct} ({judge})")
                        if "question" in data:
                            print(f"  问题: {data['question']}")
                        if "answer" in data:
                            print(f"  答案: {data['answer']}")
                        if "prediction" in data:
                            print(f"  预测: {data['prediction']}")
                        break
                except:
                    continue
    
    if not found:
        print(f"未找到问题ID: {qid}")
        print("可用的ID示例:")
        # 随便找个文件显示几个ID
        for filename in MODEL_FILES:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= 5:
                            break
                        try:
                            data = json.loads(line)
                            print(f"  {data.get('questionId')}")
                        except:
                            continue
                break

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        show_question_results(sys.argv[1])
    else:
        print("用法: python script.py <questionId>")
        print("示例: python script.py 172")