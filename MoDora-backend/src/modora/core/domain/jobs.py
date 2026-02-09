from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class BuildTreeJob:
    """构建树任务的数据类"""
    num: int
    pdf_path: Path
    co_path: Path
    out_dir: Path
    title_path: Path
    tree_path: Path

@dataclass
class QAJob:
    """QA 任务的数据类，包含问题、PDF 路径、树路径和答案等信息"""
    question_id: int
    question: str
    pdf_path: Path
    tree_path: Path
    answer: str  # Ground truth (标准答案)
    output_path: Path

@dataclass(frozen=True)
class PreprocessJob:
    """预处理任务的数据类"""
    idx: int
    pdf_path: str
    out_dir: str
    res_path: str
    co_path: str
