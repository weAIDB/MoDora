from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from tqdm import tqdm

from modora.core.domain import CCTree
from modora.core.infra.logging.setup import configure_logging
from modora.core.infra.pdf.cropper import ImageCache, crop_bboxes_to_base64_list
from modora.core.settings import Settings
from modora.core.utils.fs import iter_pdf_paths


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("cache-images", help="Precompute image cache for bbox crops")
    p.add_argument(
        "--dataset",
        default="/home/yukai/project/MoDora/datasets/MMDA",
        help="Path to a PDF file or directory",
    )
    p.add_argument(
        "--cache-dir", default=None, help="Cache directory containing tree.json"
    )
    p.set_defaults(_handler=_handle_cache_images)


def _iter_locations(node) -> list:
    items = []
    locs = getattr(node, "location", None) or []
    items.extend(locs)
    children = getattr(node, "children", None) or {}
    for child in children.values():
        items.extend(_iter_locations(child))
    return items


def _resolve_tree_path(pdf_path: Path, cache_dir: Path) -> Path | None:
    stem = pdf_path.stem
    path_a = cache_dir / stem / "tree.json"
    if path_a.exists():
        return path_a
    path_b = cache_dir / "trees" / stem / "tree.json"
    if path_b.exists():
        return path_b
    return None


def _handle_cache_images(args: argparse.Namespace, logger: logging.Logger) -> int:
    config_path = (getattr(args, "config", None) or "").strip() or None
    if config_path:
        os.environ["MODORA_CONFIG"] = config_path

    settings = Settings.load(config_path)
    configure_logging(settings)

    dataset = getattr(args, "dataset", None) or settings.docs_dir
    cache_dir = Path(getattr(args, "cache_dir", None) or settings.cache_dir)
    if not dataset:
        logger.error("no dataset specified")
        return 2

    pdf_paths = list(iter_pdf_paths(str(dataset)))
    if not pdf_paths:
        logger.error("no pdf files found")
        return 2

    cache = ImageCache(cache_dir / "image_cache.db")
    pbar = tqdm(total=len(pdf_paths), unit="pdf", dynamic_ncols=True)
    try:
        for pdf_path in pdf_paths:
            tree_path = _resolve_tree_path(pdf_path, cache_dir)
            if not tree_path or not tree_path.exists():
                pbar.update(1)
                continue

            try:
                tree = CCTree.load_json(str(tree_path))
            except Exception as e:
                logger.error(
                    "failed to load tree",
                    extra={
                        "pdf": str(pdf_path),
                        "tree": str(tree_path),
                        "error": str(e),
                    },
                )
                pbar.update(1)
                continue

            locations = _iter_locations(tree.root)
            if not locations:
                pbar.update(1)
                continue

            seen = set()
            bbox_data = []
            for loc in locations:
                page = int(getattr(loc, "page", 0) or 0)
                bbox = getattr(loc, "bbox", None) or []
                if not isinstance(bbox, list) or len(bbox) != 4:
                    continue
                nb = [round(float(x), 2) for x in bbox[:4]]
                key = (page, tuple(nb))
                if key in seen:
                    continue
                seen.add(key)
                bbox_data.append({"page": page, "bbox": nb})

            if not bbox_data:
                pbar.update(1)
                continue

            b64_list = crop_bboxes_to_base64_list(str(pdf_path), bbox_data)
            items: list[tuple[str, int, list[float], str]] = []
            for data, b64 in zip(bbox_data, b64_list):
                if not b64:
                    continue
                items.append((str(pdf_path), data["page"], data["bbox"], b64))
            cache.set_batch(items)
            pbar.update(1)
    finally:
        pbar.close()

    return 0
