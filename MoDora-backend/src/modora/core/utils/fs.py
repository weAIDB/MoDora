import re
from pathlib import Path
from typing import Iterator

def natural_key(text: str) -> list[str | int]:
    """
    用于文件名自然排序的 key 函数。
    例如：['1.pdf', '2.pdf', '10.pdf'] 而不是 ['1.pdf', '10.pdf', '2.pdf']
    """
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]

def iter_pdf_paths(dataset_dir: str | Path) -> Iterator[Path]:
    """
    迭代目录下的所有 PDF 文件，并按自然顺序排序。
    """
    p = Path(dataset_dir)
    if not p.is_dir():
        return
    
    # 查找所有 .pdf 文件（不区分大小写）
    pdf_paths = [
        f for f in p.iterdir() 
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]
    
    # 按自然顺序排序
    pdf_paths.sort(key=lambda x: natural_key(x.name))
    
    yield from pdf_paths
