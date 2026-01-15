import json
import os
import glob
from collections import defaultdict

# 定义文件名到图表 Label 的映射
FILE_TO_LABEL = {
    "resudop.jsonl": "UDOP",
    "resdocowl.jsonl": "DocOwl2",
    "resm3rag.jsonl": "M3DocRAG",
    "restxtrag.jsonl": "TextRAG",
    "ressvrag.jsonl": "SV-RAG",
    "reszendb.jsonl": "ZenDB",
    "resgpt5.jsonl": "GPT-5",
    "resquest.jsonl": "QUEST",
    "res_gpt_new.jsonl": "MoDora"  # 你的方法
}

# 收集所有模型的结果
def collect_results():
    results = defaultdict(dict)  # questionId -> {model_name: judge}
    
    files = glob.glob("res*.jsonl")
    
    for f_path in files:
        f_name = os.path.basename(f_path)
        if f_name not in FILE_TO_LABEL:
            continue
            
        model_name = FILE_TO_LABEL[f_name]
        with open(f_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    q_id = item.get("questionId")
                    judge = item.get("judge", "F")
                    # 简化为是否正确 (T/F)
                    is_correct = "T" in judge
                    
                    if q_id not in results:
                        results[q_id] = {}
                    results[q_id][model_name] = {
                        'correct': is_correct,
                        'data': item  # 保存完整数据用于后续分析
                    }
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"解析 {f_name} 时出错: {e}")
                    continue
    
    return results

# 找出MoDora做对但其他都做错的问题
def find_unique_correct_cases(results):
    unique_cases = []
    baseline_models = list(FILE_TO_LABEL.values())
    baseline_models.remove("MoDora")  # 去除MoDora
    
    for q_id, model_results in results.items():
        # 检查MoDora是否存在且做对了
        if "MoDora" not in model_results:
            continue
            
        if not model_results["MoDora"]['correct']:
            continue
            
        # 检查其他所有baseline是否都做错了
        all_others_wrong = True
        for model_name in baseline_models:
            if model_name in model_results and model_results[model_name]['correct']:
                all_others_wrong = False
                break
        
        if all_others_wrong:
            unique_cases.append({
                'questionId': q_id,
                'MoDora_correct': True,
                'MoDora_data': model_results["MoDora"]['data'],
                'other_models': {
                    model_name: {
                        'correct': model_results.get(model_name, {}).get('correct', False),
                        'present': model_name in model_results
                    }
                    for model_name in baseline_models
                }
            })
    
    return unique_cases

# 分析这些独特案例的特点
def analyze_unique_cases(unique_cases):
    print(f"找到 {len(unique_cases)} 个MoDora做对但其他baseline都做错的案例")
    
    if not unique_cases:
        return
    
    # 按基准集统计
    benchmarks = defaultdict(int)
    question_types = defaultdict(int)
    
    for case in unique_cases:
        data = case['MoDora_data']
        # 判断基准集
        benchmark = "DUDE" if "answer_type" in data else "MMDA"
        benchmarks[benchmark] += 1
        
        # 提取问题类型（如果有的话）
        if "question_type" in data:
            q_type = data["question_type"]
            question_types[q_type] += 1
        elif "answer_type" in data:
            q_type = data["answer_type"]
            question_types[q_type] += 1
    
    print("\n=== 统计信息 ===")
    print(f"基准集分布:")
    for bench, count in benchmarks.items():
        print(f"  {bench}: {count} 个案例 ({count/len(unique_cases)*100:.1f}%)")
    
    print(f"\n问题类型分布:")
    for q_type, count in question_types.items():
        print(f"  {q_type}: {count} 个案例")
    
    return unique_cases

# 保存结果到文件
def save_results(unique_cases):
    # 保存详细结果
    output_file = "modora_unique_correct_cases.json"
    
    simplified_cases = []
    for case in unique_cases:
        simplified = {
            'questionId': case['questionId'],
            'benchmark': "DUDE" if "answer_type" in case['MoDora_data'] else "MMDA",
            'question': case['MoDora_data'].get('question', ''),
            'answer': case['MoDora_data'].get('answer', ''),
            'MoDora_prediction': case['MoDora_data'].get('prediction', ''),
            'other_models_results': case['other_models']
        }
        # 添加额外信息
        if 'question_type' in case['MoDora_data']:
            simplified['question_type'] = case['MoDora_data']['question_type']
        elif 'answer_type' in case['MoDora_data']:
            simplified['answer_type'] = case['MoDora_data']['answer_type']
        
        simplified_cases.append(simplified)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified_cases, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存到: {output_file}")
    
    # 保存摘要统计
    summary_file = "modora_unique_correct_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"MoDora独特正确案例分析报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"总案例数: {len(unique_cases)}\n\n")
        
        f.write("按基准集分布:\n")
        benchmarks = defaultdict(int)
        for case in unique_cases:
            bench = "DUDE" if "answer_type" in case['MoDora_data'] else "MMDA"
            benchmarks[bench] += 1
        
        for bench, count in benchmarks.items():
            f.write(f"  {bench}: {count} 个案例 ({count/len(unique_cases)*100:.1f}%)\n")
        
        f.write("\n案例ID列表:\n")
        for i, case in enumerate(unique_cases, 1):
            bench = "DUDE" if "answer_type" in case['MoDora_data'] else "MMDA"
            f.write(f"{i:3d}. {case['questionId']} ({bench})\n")
    
    print(f"摘要报告已保存到: {summary_file}")

# 显示一些示例
def show_examples(unique_cases, num_examples=3):
    print(f"\n=== 示例案例 (前{num_examples}个) ===")
    
    for i in range(min(num_examples, len(unique_cases))):
        case = unique_cases[i]
        data = case['MoDora_data']
        
        print(f"\n示例 {i+1}:")
        print(f"问题ID: {case['questionId']}")
        print(f"基准集: {'DUDE' if 'answer_type' in data else 'MMDA'}")
        print(f"问题: {data.get('question', 'N/A')}")
        print(f"正确答案: {data.get('answer', 'N/A')}")
        print(f"MoDora预测: {data.get('prediction', 'N/A')}")
        print(f"MoDora判断: {'正确' if case['MoDora_correct'] else '错误'}")
        
        # 统计其他模型的情况
        correct_others = []
        missing_others = []
        wrong_others = []
        
        for model_name, result in case['other_models'].items():
            if not result['present']:
                missing_others.append(model_name)
            elif result['correct']:
                correct_others.append(model_name)
            else:
                wrong_others.append(model_name)
        
        print(f"其他模型: {len(wrong_others)}个错误, {len(correct_others)}个正确, {len(missing_others)}个缺失")
        if correct_others:
            print(f"  正确的模型: {', '.join(correct_others)}")
        print("=" * 80)

def main():
    print("开始分析MoDora独特正确案例...")
    
    # 1. 收集所有结果
    print("收集所有模型的结果...")
    results = collect_results()
    print(f"收集到 {len(results)} 个唯一问题ID")
    
    # 2. 找出MoDora独特正确的案例
    print("分析MoDora独特正确案例...")
    unique_cases = find_unique_correct_cases(results)
    
    # 3. 分析统计
    analyze_unique_cases(unique_cases)
    
    # 4. 显示示例
    if unique_cases:
        show_examples(unique_cases, num_examples=5)
        
        # 5. 保存结果
        save_results(unique_cases)
        
        print(f"\n✅ 分析完成！找到了 {len(unique_cases)} 个MoDora独特正确的案例。")
    else:
        print("❌ 未找到MoDora独特正确的案例。")

if __name__ == "__main__":
    main()