from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildTreeJob:
    """Data class for tree construction tasks."""

    num: int
    pdf_path: Path
    co_path: Path
    out_dir: Path
    title_path: Path
    tree_path: Path


@dataclass
class QAJob:
    """Data class for QA tasks, containing information such as questions, PDF paths, tree paths, and answers."""

    question_id: int
    question: str
    pdf_path: Path
    tree_path: Path
    answer: str  # Ground truth (standard answer)
    output_path: Path


@dataclass(frozen=True)
class PreprocessJob:
    """Data class for preprocessing tasks."""

    idx: int
    pdf_path: str
    out_dir: str
    res_path: str
    co_path: str
