import time
import glob
import json
import os

from tqdm import tqdm
import Levenshtein

from api_utils import *
from prompt_template import *
from constants import *

from concurrent.futures import ThreadPoolExecutor, as_completed

def is_equal(query, references, prediction):
    for reference in references:

        # Cotainment Check
        if reference.lower() in prediction.lower():
            return "T"

        # AI Check
        prompt = evaluation_prompt.format(query=query, a=reference, b=prediction)
        res = gpt_generate(prompt)
        if "T" in res:
            return "T"

    return "F"

def bool_string(s):
    s = s.lower()
    if s == "true" or s == "t" or s == "yes" or s == "y" or s == "1" or s == "on":
        return True
    return False

def check_answer(query, answer):
    prompt = check_answer_prompt.format(query=query, answer=answer)
    res = gpt_generate(prompt)   
    return bool_string(res)

def anls_single_sample(prediction, references, threshold=0.5):
    
    max_nls = 0.0
    pred_str = prediction if prediction is not None else ""
    
    # Calculate max NLS between each reference and prediction
    for reference in references:
        distance = Levenshtein.distance(pred_str, reference)
        max_len = max(len(pred_str), len(reference))
        if max_len == 0:
            nls = 1.0
        else:
            nls = 1.0 - float(distance) / max_len
        
        if nls > max_nls:
            max_nls = nls

    return max_nls if max_nls > threshold else 0.0


def evaluate(input_file, output_file):
    
    # Prepare
    anls_score = 0.0

    dir_path = os.path.dirname(output_file)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    data = []
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    res = []
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as file:
            for line in file:
                res.append(json.loads(line.strip()))
    
    # Adapt different answer formats in datasets
    for row in tqdm(data, desc="Processing..."):
        row["answer"] = [row["answer"]] if "answer" in row else [", ".join(row["answers"])] + row["answers_variants"]

    # Single processing for LLM T/F judging 
    def process_row(row,res):

        flag = False
        query = row["question"]
        
        # Skip processed id in results
        for x in res:
            if x is None:
                continue
            if row["questionId"] == x["questionId"]:
                flag = True
                break
        if flag:
            return
        
        # Special process for not-answerable questions in DUDE
        if "answer_type" in row and row["answer_type"] == "not-answerable":
            if not check_answer(query, row["prediction"]):
                row["judge"] = "T"
            else:
                row["judge"] = "F"
            res.append(row)
            with open(output_file, "a", encoding="utf-8") as file:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
            return
        
        try:
            judge = is_equal(query, row["answer"], row["prediction"])
        except Exception as e:
            print(row["questionId"])
            print(row["answer"])
            print(row["prediction"])
            judge = "F"
            print(f"Error: {e}")
        
        row["judge"] = judge
        res.append(row)

        with open(output_file, "a", encoding="utf-8") as file:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
        return

    # Concurrent LLM calls
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {
            executor.submit(process_row, row, res): row
            for row in data
        }
        for future in tqdm(as_completed(future_to_item), desc="Processing dataset:", total=len(data)):
            complete = True

    # Rank by Id
    with open(evaluation_path, 'r', encoding='utf-8') as f:
        items = [json.loads(line) for line in f]
    items.sort(key=lambda x: x['questionId'])
    with open(evaluation_path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Calculate AIC-Acc
    correct = 0
    total = len(res)
    for row in res:
        if "T" in row["judge"]:
            correct += 1
    accuracy = correct / total
    print(f"{input_file} Accuracy: {accuracy}")

    # Calculate ACNLS
    total = len(res)
    for row in res:

        # Cotainment Check
        contain = False
        for answer in row["answer"]:
            if answer.lower() in row["prediction"].lower() and answer != "":
                contain = True
        if contain:
            anls_score += 1
        
        # Special process for not-answerable questions in DUDE
        elif "answer_type" in row and row["answer_type"] == "not-answerable" and "T" in row["judge"]:
            anls_score += 1
        
        else:
            anls_score += anls_single_sample(
                prediction=row["prediction"],
                references=row["answer"],
                threshold=0.5
            )
    anls_avg = anls_score / total
    print(f"{input_file} ANLS: {anls_avg}")

if __name__ == "__main__":
    output_path = os.path.join(OUTPUT_DIR, os.path.basename(SOURCE_DIR), "res.json")
    evaluation_path = os.path.join(EVALUATION_DIR, os.path.basename(SOURCE_DIR), "res.jsonl")
    evaluate(output_path, evaluation_path)

    
