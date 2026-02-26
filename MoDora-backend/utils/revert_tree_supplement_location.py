import json
import logging
import argparse
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("revert_tree")


def clear_container_locations(node_data: dict[str, Any]):
    """
    Recursively clear locations for container nodes like Supplement, Header, etc.
    """
    node_type = node_data.get("type", "")
    # List of types that are purely containers and shouldn't hold aggregated locations
    container_types = ["supplement", "header", "footer", "number", "aside_text"]

    if node_type in container_types:
        # Clear location
        node_data["location"] = []

    # Recurse
    children = node_data.get("children", {})
    if children:
        for child_node in children.values():
            clear_container_locations(child_node)


def process_file(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = data.get("root", data)
        children = root.get("children", {})

        if "Supplement" in children:
            # logger.info(f"Reverting Supplement locations in {file_path}")
            clear_container_locations(children["Supplement"])

        # Save back as formatted JSON with indent
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Revert Supplement container locations in tree.json files"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="/home/yukai/project/MoDora/MoDora-backend/cache_v4",
        help="Directory containing cache folders",
    )
    args = parser.parse_args()

    base_dir = Path(args.dir)
    files = list(base_dir.glob("**/tree.json"))
    logger.info(f"Found {len(files)} tree.json files.")

    for i, file_path in enumerate(files):
        if (i + 1) % 100 == 0:
            logger.info(f"Processed {i + 1}/{len(files)} files...")
        process_file(file_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()
