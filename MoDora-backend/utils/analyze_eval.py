import json
import os
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import Levenshtein
from pathlib import Path

def get_nls(prediction, references, threshold=0.5):
    """
    Calculate Normalized Levenshtein Similarity (ANLS) for a single sample.
    """
    max_nls = 0.0
    pred_str = str(prediction).lower() if prediction is not None else ""
    
    # Handle single string reference or list
    if isinstance(references, str):
        references = [references]
    elif not isinstance(references, list):
        references = []

    for ref in references:
        ref_str = str(ref).lower()
        dist = Levenshtein.distance(pred_str, ref_str)
        max_len = max(len(pred_str), len(ref_str))
        
        if max_len == 0:
            nls = 1.0
        else:
            nls = 1.0 - (dist / max_len)
            
        max_nls = max(max_nls, nls)
        
    return max_nls if max_nls > threshold else 0.0

def load_and_process_data(file_path):
    """
    Load evaluation results from JSONL and calculate metrics per item.
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                
                tag = item.get("tag", "Unknown")
                category = "Unknown"
                if isinstance(tag, str) and "-" in tag:
                    try:
                        # User specified: "1-1" -> category 1, "2-3" -> category 3
                        # So we take the part after the hyphen
                        category = tag.split("-")[-1]
                    except Exception:
                        pass

                judge = item.get("judge", "F")
                prediction = item.get("prediction", "")
                answer = item.get("answer", [])
                
                # Accuracy: 1 if judge is T, else 0
                acc = 1.0 if judge == "T" else 0.0
                
                # ACNLS Calculation Logic:
                # 1. Containment Check: If any answer is in prediction (case-insensitive) -> ACNLS = 1.0
                # 2. Else: Calculate ANLS using Levenshtein distance
                
                acnls = 0.0
                contain = False
                
                # Ensure prediction is a string
                pred_str = str(prediction).lower() if prediction is not None else ""
                
                # Check for containment
                if answer:
                    for ans in answer:
                        ans_str = str(ans).lower()
                        if ans_str and ans_str in pred_str:
                            contain = True
                            break
                
                if contain:
                    acnls = 1.0
                else:
                    acnls = get_nls(prediction, answer)
                
                data.append({
                    "tag": tag,
                    "category": category,
                    "Accuracy": acc,
                    "ACNLS": acnls
                })
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line}")
                continue
                
    return pd.DataFrame(data)

def plot_charts(df, output_dir):
    """
    Generate and save charts for Accuracy and ACNLS per tag.
    """
    if df.empty:
        print("No data to plot.")
        return

    # Group by tag and calculate mean
    grouped = df.groupby("tag")[["Accuracy", "ACNLS"]].mean().reset_index()
    
    # Sort by tag for consistent plotting
    grouped = grouped.sort_values("tag")
    
    # Setup plot style
    sns.set_theme(style="whitegrid")
    
    # 1. Plot Accuracy
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(x="tag", y="Accuracy", data=grouped, hue="tag", palette="viridis", legend=False)
    plt.title("Accuracy per Tag", fontsize=16)
    plt.ylabel("Accuracy", fontsize=14)
    plt.xlabel("Tag", fontsize=14)
    plt.ylim(0, 1.1)
    
    # Add value labels
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha='center', va='center', 
                   xytext=(0, 9), textcoords='offset points')
                   
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "accuracy_per_tag.png"))
    plt.close()
    
    # 2. Plot ACNLS
    plt.figure(figsize=(12, 6))
    ax = sns.barplot(x="tag", y="ACNLS", data=grouped, hue="tag", palette="magma", legend=False)
    plt.title("ACNLS per Tag", fontsize=16)
    plt.ylabel("ACNLS", fontsize=14)
    plt.xlabel("Tag", fontsize=14)
    plt.ylim(0, 1.1)
    
    # Add value labels
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha='center', va='center', 
                   xytext=(0, 9), textcoords='offset points')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "acnls_per_tag.png"))
    plt.close()
    
    # 3. Save Summary CSV
    grouped.to_csv(os.path.join(output_dir, "metrics_summary_by_tag.csv"), index=False)
    print(f"Charts and summary saved to {output_dir}")
    print("\nSummary by Tag:")
    print(grouped)

    # 4. Group by Category and Calculate Metrics
    category_grouped = df.groupby("category")[["Accuracy", "ACNLS"]].mean().reset_index()
    category_grouped = category_grouped.sort_values("category")
    
    # Save Category Summary
    category_grouped.to_csv(os.path.join(output_dir, "metrics_summary_by_category.csv"), index=False)
    
    print("\nSummary by Category:")
    print(category_grouped)
    
    # Plot Category Accuracy
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x="category", y="Accuracy", data=category_grouped, hue="category", palette="viridis", legend=False)
    plt.title("Accuracy per Category", fontsize=16)
    plt.ylabel("Accuracy", fontsize=14)
    plt.xlabel("Category", fontsize=14)
    plt.ylim(0, 1.1)
    
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha='center', va='center', 
                   xytext=(0, 9), textcoords='offset points')
                   
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "accuracy_per_category.png"))
    plt.close()

    # Plot Category ACNLS
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x="category", y="ACNLS", data=category_grouped, hue="category", palette="magma", legend=False)
    plt.title("ACNLS per Category", fontsize=16)
    plt.ylabel("ACNLS", fontsize=14)
    plt.xlabel("Category", fontsize=14)
    plt.ylim(0, 1.1)
    
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.2f}', 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha='center', va='center', 
                   xytext=(0, 9), textcoords='offset points')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "acnls_per_category.png"))
    plt.close()
    
    # Overall metrics
    print("\nOverall Metrics:")
    print(df[["Accuracy", "ACNLS"]].mean())

def main():
    parser = argparse.ArgumentParser(description="Analyze evaluation results by tag.")
    parser.add_argument(
        "--input", 
        default="/home/yukai/project/MoDora/MoDora-backend/tmp/gemini/eval.jsonl",
        help="Path to the evaluation jsonl file"
    )
    parser.add_argument(
        "--output-dir", 
        default="/home/yukai/project/MoDora/MoDora-backend/utils",
        help="Directory to save charts and summary"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    
    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        return
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {input_path}...")
    df = load_and_process_data(input_path)
    plot_charts(df, str(output_dir))

if __name__ == "__main__":
    main()
