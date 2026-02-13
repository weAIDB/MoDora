#!/usr/bin/env python3
"""
Script to locate Chinese characters in Python codebase.
Only outputs the first 3 results to keep context clean.
"""

import os
import re
import tokenize
from io import BytesIO


def locate_chinese(directory: str = "."):
    """Scan Python files and locate Chinese characters."""
    exclude_dirs = {
        "venv",
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "env",
        "build",
        "dist",
    }
    results = []
    pattern = re.compile(r"[\u4e00-\u9fff]+")

    for root, dirs, files in os.walk(directory):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, "rb") as f:
                    content = f.read()

                tokens = list(tokenize.tokenize(BytesIO(content).readline))

                for token in tokens:
                    if token.type in (tokenize.STRING, tokenize.COMMENT):
                        if pattern.search(token.string):
                            # Determine type
                            t_type = (
                                "comment"
                                if token.type == tokenize.COMMENT
                                else "string"
                            )

                            # Extract clean content
                            text = token.string.strip()
                            if token.type == tokenize.STRING:
                                # Remove quotes and prefixes
                                text = text.lstrip("rRfFbBuU").strip("\"'")

                            results.append(
                                {
                                    "file": os.path.relpath(filepath, directory),
                                    "line": token.start[0],
                                    "type": t_type,
                                    "content": text[:100],  # Truncate long strings
                                }
                            )

            except Exception:
                continue

    return results


if __name__ == "__main__":
    print("🔍 Scanning for Chinese characters...\n")

    found = locate_chinese(".")

    if not found:
        print("✅ No Chinese characters found.")
    else:
        print(f"📊 Total found: {len(found)} occurrences\n")
        print("First 3 items for preview:\n")

        for item in found[:3]:
            print(f"File:   {item['file']}")
            print(f"Line:   {item['line']}")
            print(f"Type:   {item['type']}")
            print(f"Text:   {item['content']}")
            print("-" * 40)

        if len(found) > 3:
            print(f"... and {len(found) - 3} more items not shown.")
