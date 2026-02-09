from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import pvariance
from typing import Any


def _classify_label(label: str | None) -> str:
    if label is None:
        return "text"
    s = str(label).strip().lower()
    if s == "chart":
        return "chart"
    if s == "image":
        return "image"
    if s == "table":
        return "table"
    if s in {"header", "footer", "aside", "aside_text", "number"}:
        return "layout_misc"
    return "text"


def _load_ocr_blocks(ocr_path: Path) -> list[dict[str, Any]]:
    if not ocr_path.exists():
        return []
    payload = json.loads(ocr_path.read_text(encoding="utf-8"))
    blocks = payload.get("blocks") if isinstance(payload, dict) else None
    if not isinstance(blocks, list):
        return []
    return [b for b in blocks if isinstance(b, dict)]


def get_component_stats(ocr_path: Path) -> tuple[dict[str, int], float, int]:
    blocks = _load_ocr_blocks(ocr_path)
    counts = {
        "chart": 0,
        "image": 0,
        "table": 0,
        "layout_misc": 0,
        "text": 0,
    }
    pages = 0
    for block in blocks:
        label = block.get("label") or block.get("block_label")
        cat = _classify_label(label)
        counts[cat] += 1
        pages = max(pages, int(block.get("page_id") or block.get("page") or 0))

    values = list(counts.values())
    variance = pvariance(values) if len(values) > 1 else 0.0
    try:
        variance = math.sqrt(variance) / max(sum(values), 1)
    except Exception:
        variance = 0.0

    return counts, variance, pages


def get_tree_stats(tree_path: Path) -> tuple[int, int, int]:
    if not tree_path.exists():
        return 0, 0, 0
    tree = json.loads(tree_path.read_text(encoding="utf-8"))

    node_cnt = 0
    leaf_cnt = 0

    def traverse(children: dict[str, Any]) -> int:
        nonlocal node_cnt, leaf_cnt
        depth = 0
        for key, node in list(children.items()):
            node_cnt += 1
            node_children = node.get("children", {}) if isinstance(node, dict) else {}
            if node_children:
                child_depth = traverse(node_children)
                if child_depth > depth and key != "Supplement":
                    depth = child_depth
            else:
                leaf_cnt += 1
        return depth + 1

    depth = traverse(tree.get("children", {}) if isinstance(tree, dict) else {})
    return node_cnt, leaf_cnt, depth + 1
