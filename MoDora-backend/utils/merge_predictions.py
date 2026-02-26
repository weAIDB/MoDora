import json
from pathlib import Path


def merge_previous_predictions(rerun_correct_path, original_eval_path):
    """
    Merge previous predictions from original evaluation results into rerun correct results.
    """
    rerun_path = Path(rerun_correct_path)
    original_path = Path(original_eval_path)

    if not rerun_path.exists():
        print(f"Error: Rerun file not found at {rerun_path}")
        return

    if not original_path.exists():
        print(f"Error: Original file not found at {original_path}")
        return

    # 1. Load Original Predictions (Map Question ID -> Prediction)
    original_preds = {}
    with open(original_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                qid = item.get("questionId")
                if qid is not None:
                    original_preds[qid] = item.get("prediction", "")
            except json.JSONDecodeError:
                continue

    # 2. Process Rerun Correct File
    updated_items = []

    print("\n--- Previous Predictions for Recovered Cases ---")

    with open(rerun_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                qid = item.get("questionId")

                # Find previous prediction
                prev_pred = original_preds.get(qid, "N/A")
                item["previous_prediction"] = prev_pred

                updated_items.append(item)

                # Print Info
                print(f"QID: {qid} | Tag: {item.get('tag')}")
                print(f"  Question: {item.get('question')}")
                print(f"  Previous: {prev_pred}")
                print(f"  Current:  {item.get('prediction')}")
                print("-" * 40)

            except json.JSONDecodeError:
                continue

    # 3. Save Updated File
    with open(rerun_path, "w", encoding="utf-8") as f:
        for item in updated_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nUpdated {len(updated_items)} items in {rerun_path}")


if __name__ == "__main__":
    RERUN_CORRECT_PATH = (
        "/home/yukai/project/MoDora/MoDora-backend/tmp/rerun_correct.jsonl"
    )
    ORIGINAL_EVAL_PATH = (
        "/home/yukai/project/MoDora/MoDora-backend/tmp/gemini/eval.jsonl"
    )

    merge_previous_predictions(RERUN_CORRECT_PATH, ORIGINAL_EVAL_PATH)
