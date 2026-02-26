import json
import logging
import argparse
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fix_tree")


def aggregate_locations(node_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Recursively aggregate locations from children to the current node.
    Returns the aggregated list of locations for the current node.
    """
    children = node_data.get("children", {})
    current_locations = node_data.get("location", []) or []

    # If node already has locations, we might still want to merge children's locations
    # especially for container nodes like Supplement, Header, etc. which usually start empty.
    # However, for normal content nodes, we probably don't want to duplicate children's locations
    # into parent if parent already has its own location (e.g. Section title).

    # Target specific container nodes that are known to lack location
    node_type = node_data.get("type", "")
    is_container = node_type in [
        "supplement",
        "header",
        "footer",
        "number",
        "aside_text",
        "root",
    ]

    children_locations = []
    if children:
        for child_key, child_node in children.items():
            child_locs = aggregate_locations(child_node)
            children_locations.extend(child_locs)

    if is_container:
        # For containers, we aggregate all children locations
        # De-duplicate based on page and bbox to avoid massive lists?
        # For simplicity, just extend. The retriever handles lists.
        # But let's avoid duplicates if exact same dict object or value.

        # Simple merge
        all_locs = current_locations + children_locations

        # Optional: Deduplicate (might be slow for huge lists, skip for now unless needed)
        node_data["location"] = all_locs
        return all_locs

    return current_locations


def process_file(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = data.get("root", data)  # Handle if wrapped in "root" or direct node

        # Find Supplement node
        children = root.get("children", {})
        if "Supplement" in children:
            logger.info(f"Fixing Supplement locations in {file_path}")
            aggregate_locations(children["Supplement"])

            # Save back
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)  # remove indent for smaller size
        else:
            logger.debug(f"No Supplement node found in {file_path}")

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Fix missing locations in Supplement nodes of tree.json files"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="/home/yukai/project/MoDora/MoDora-backend/cache_v4",
        help="Directory containing cache folders",
    )
    args = parser.parse_args()

    base_dir = Path(args.dir)
    if not base_dir.exists():
        logger.error(f"Directory not found: {base_dir}")
        return

    # Find all tree.json files recursively
    files = list(base_dir.glob("**/tree.json"))
    logger.info(f"Found {len(files)} tree.json files.")

    for i, file_path in enumerate(files):
        if (i + 1) % 100 == 0:
            logger.info(f"Processed {i + 1}/{len(files)} files...")
        process_file(file_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()
