import json
import os
import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import Levenshtein
from matplotlib.patches import Patch

# --- 1. 配置路径与字体 ---
# 请确保这些字体文件在当前目录下，否则请修改为系统自带字体名
FONT_PATH = './TIMES.TTF'  
FONT_BOLD_PATH = './TIMESBD.TTF' 
try:
    font_prop = fm.FontProperties(fname=FONT_PATH)
    font_bold_prop = fm.FontProperties(fname=FONT_BOLD_PATH)
except:
    print("未找到指定字体文件，将使用系统默认字体")
    font_prop = fm.FontProperties()
    font_bold_prop = fm.FontProperties()

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
    "res_gpt_new.jsonl": "MoDora" # my approach
}

# 绘图时的顺序
BASELINE_ORDER = ["UDOP", "DocOwl2", "M3DocRAG", "TextRAG", "SV-RAG", "ZenDB", "QUEST", "GPT-5", "MoDora"]

# --- 2. 数据处理逻辑 ---
def get_nls(prediction, references, threshold=0.5):
    max_nls = 0.0
    pred_str = str(prediction).lower() if prediction else ""
    for ref in references:
        ref_str = str(ref).lower()
        dist = Levenshtein.distance(pred_str, ref_str)
        max_len = max(len(pred_str), len(ref_str))
        nls = 1.0 - (dist / max_len) if max_len > 0 else 1.0
        max_nls = max(max_nls, nls)
    return max_nls if max_nls > threshold else 0.0

def process_files():
    results = []
    files = glob.glob("res*.jsonl")
    
    for f_path in files:
        f_name = os.path.basename(f_path)
        if f_name not in FILE_TO_LABEL: continue # 过滤掉不在列表中的文件
        
        label = FILE_TO_LABEL[f_name]
        with open(f_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                benchmark = "DUDE" if "answer_type" in item else "MMDA"
                judge = item.get("judge", "F")

                results.append({
                    "Baseline": label,
                    "Benchmark": benchmark,
                    "AIC-Acc (%)": 100.0 if "T" in judge else 0.0
                })
    return pd.DataFrame(results)

# --- 3. 绘图逻辑 ---
def draw_paper_plot(df):
    # 计算均值
    plot_df = df.groupby(['Baseline', 'Benchmark'], observed=True).mean().reset_index()
    # 强制排序
    plot_df['Baseline'] = pd.Categorical(plot_df['Baseline'], categories=BASELINE_ORDER, ordered=True)
    plot_df = plot_df.sort_values('Baseline')

    # 设置主题：白色网格
    sns.set_theme(style="whitegrid")
    
    # 调色盘：使用 Greys (灰度) 或粘贴一组低饱和度颜色
    # 这里使用 husl 系统生成低饱和度颜色，或者直接定义一组灰色调
    low_sat_palette = sns.color_palette("Set3", n_colors=len(BASELINE_ORDER))
    
    fig, ax = plt.subplots(figsize=(10, 5))

    # 绘制 AIC-Acc (%)
    sns.barplot(
        data=plot_df, 
        x="Benchmark", 
        y="AIC-Acc (%)", 
        hue="Baseline", 
        ax=ax, 
        palette=low_sat_palette, # 使用灰度调色盘
        edgecolor="black", 
        linewidth=0.8
    )

    # 细节设置
    ax.set_ylim(0, 110)
    ax.set_ylabel("AIC-Accuracy (%)", fontproperties=font_bold_prop, fontsize=14)
    ax.set_xlabel("")
    
    # 设置刻度字体
    ax.tick_params(axis='both', which='major', labelsize=16)
    for label in ax.get_xticklabels():
        label.set_fontproperties(font_bold_prop)
        label.set_fontsize(16)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font_prop)

    # 数值标注 - 仅对 MoDora 加粗
    for i, p in enumerate(ax.patches):
        height = p.get_height()
        if height > 0:
            # 计算当前柱子属于哪个模型
            # 每个基准组有 len(BASELINE_ORDER) 个柱子
            group_idx = i // len(BASELINE_ORDER)  # 0 表示 DUDE，1 表示 MMDA
            baseline_idx = i % len(BASELINE_ORDER)  # 在当前组中的位置
            
            # 检查是否对应 MoDora
            if BASELINE_ORDER[baseline_idx] == "MoDora":
                # MoDora 使用粗体字体
                ax.annotate(f'{height:.1f}', 
                            (p.get_x() + p.get_width() / 2., height), 
                            ha='center', va='center', fontsize=16, 
                            fontproperties=font_bold_prop,  # 使用粗体字体
                            xytext=(0, 8), 
                            textcoords='offset points', 
                            rotation=0,
                            weight='bold')  # 加粗
            else:
                # 其他模型保持原样
                ax.annotate(f'{height:.1f}', 
                            (p.get_x() + p.get_width() / 2., height), 
                            ha='center', va='center', fontsize=16, 
                            fontproperties=font_prop,  # 普通字体
                            xytext=(0, 8), 
                            textcoords='offset points', 
                            rotation=0)

    # 为柱子添加斜线纹理
    num_baselines = len(BASELINE_ORDER)
    for i, patch in enumerate(ax.patches):
        if i % num_baselines % 2 == 0:
            patch.set_hatch('///')  # 偶数索引的柱子添加斜线

    # 获取原始图例并创建带纹理的图例
    handles, labels = ax.get_legend_handles_labels()
    
    # 创建新的带纹理的图例手柄
    new_handles = []
    for i, (handle, label) in enumerate(zip(handles, labels)):
        # 复制原始的颜色和边缘
        new_handle = Patch(facecolor=handle.get_facecolor(), 
                          edgecolor='black',
                          linewidth=0.8)
        
        # 为偶数索引的图例添加同样的斜线纹理
        if i % 2 == 0:
            new_handle.set_hatch('///')
        
        new_handles.append(new_handle)
    
    # 使用带纹理的图例
    ax.legend(new_handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.25),
               ncol=len(BASELINE_ORDER)//2 + 1, prop=font_bold_prop, frameon=False, fontsize=16)

    plt.tight_layout()
    plt.savefig("paper_evaluation_acc_only.pdf", bbox_inches='tight')
    plt.savefig("paper_evaluation_acc_only.svg", format="svg", bbox_inches='tight')
    print("分析完成！仅展示 AIC-Acc 的灰度图已保存。")

if __name__ == "__main__":
    raw_data = process_files()
    if not raw_data.empty:
        draw_paper_plot(raw_data)
        summary = raw_data.groupby(['Benchmark', 'Baseline'], observed=True).mean()
        summary.to_csv("acc_summary.csv")
    else:
        print("未找到对应的 res*.jsonl 文件，请检查路径。")