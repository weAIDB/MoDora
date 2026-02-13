import re
from pathlib import Path
from typing import Iterator


def natural_key(text: str) -> list[str | int]:
    """Key function for natural sorting of filenames.

    Example:
        ['1.pdf', '2.pdf', '10.pdf'] instead of ['1.pdf', '10.pdf', '2.pdf']

    Args:
        text (str): The filename or text to be keyed.

    Returns:
        list[str | int]: A list of strings and integers for sorting.
    """
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]


def iter_pdf_paths(dataset_dir: str | Path) -> Iterator[Path]:
    """Iterate through all PDF files in the directory and sort them in natural order.

    Args:
        dataset_dir (str | Path): Path to the directory containing PDF files.

    Yields:
        Iterator[Path]: Iterator of Path objects for the PDF files.
    """
    p = Path(dataset_dir)
    if not p.is_dir():
        return

    # Find all .pdf files (case-insensitive)
    pdf_paths = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"]

    # Sort in natural order
    pdf_paths.sort(key=lambda x: natural_key(x.name))

    yield from pdf_paths
