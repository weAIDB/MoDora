import json
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path


def process_rerun_results(input_file, output_dir):
    """
    Analyze rerun evaluation results.
    1. Filter items where judge is 'T' (Correctly recovered).
    2. Save these items to rerun_correct.jsonl.
    3. Count statistics by tag.
    4. Plot the count of recovered cases per tag.
    """
    correct_items = []

    # Ensure output directories exist
    tmp_dir = Path("./tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Read and Filter
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("judge") == "T":
                    correct_items.append(item)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {line}")

    # 2. Save Correct Items
    correct_output_path = tmp_dir / "rerun_correct.jsonl"
    with open(correct_output_path, "w", encoding="utf-8") as f:
        for item in correct_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Saved {len(correct_items)} recovered cases to {correct_output_path}")

    if not correct_items:
        print("No correct cases found in the input file.")
        return

    # 3. Statistics by Tag
    df = pd.DataFrame(correct_items)
    tag_counts = df["tag"].value_counts().reset_index()
    tag_counts.columns = ["tag", "count"]
    tag_counts = tag_counts.sort_values("tag")

    print("\nRecovered Cases by Tag:")
    print(tag_counts)

    # 4. Plot Chart
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(12, 6))

    ax = sns.barplot(x="tag", y="count", data=tag_counts, palette="Greens_d")
    plt.title("Number of Correctly Recovered Cases by Tag (Rerun)", fontsize=16)
    plt.ylabel("Count", fontsize=14)
    plt.xlabel("Tag", fontsize=14)

    # Add value labels
    for p in ax.patches:
        ax.annotate(
            f"{int(p.get_height())}",
            (p.get_x() + p.get_width() / 2.0, p.get_height()),
            ha="center",
            va="center",
            xytext=(0, 9),
            textcoords="offset points",
        )

    plt.tight_layout()
    plot_path = output_dir / "rerun_recovered_counts.png"
    plt.savefig(plot_path)
    plt.close()

    print(f"Chart saved to {plot_path}")


def main():
    parser = argparse.ArgumentParser(description="Analyze rerun evaluation results.")
    parser.add_argument(
        "--input",
        default="/home/yukai/project/MoDora/MoDora-backend/tmp/evaluation.jsonl",
        help="Path to the evaluation jsonl file",
    )
    parser.add_argument(
        "--output-dir",
        default="/home/yukai/project/MoDora/MoDora-backend/utils",
        help="Directory to save charts",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        return

    print(f"Processing {input_path}...")
    process_rerun_results(input_path, output_dir)


if __name__ == "__main__":
    main()
