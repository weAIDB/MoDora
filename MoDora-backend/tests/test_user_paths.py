from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths


class UserPathsTest(unittest.TestCase):
    def test_user_paths_are_scoped_under_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_path = root / "config.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "docs_dir": str(root / "docs"),
                        "cache_dir": str(root / "cache"),
                        "storage_root": str(root / "storage"),
                        "db_path": str(root / "storage" / "modora.db"),
                        "ocr_model": "disabled",
                        "enable_ocr_preload": False,
                        "enable_vector_search": False,
                    }
                ),
                encoding="utf-8",
            )
            settings = Settings.load(str(cfg_path))
            paths = resolve_paths(settings)
            user_paths = paths.user_paths("user_123")

            self.assertEqual(user_paths.docs_dir, root / "storage" / "users" / "user_123" / "docs")
            self.assertEqual(user_paths.cache_dir, root / "storage" / "users" / "user_123" / "cache")
            self.assertEqual(user_paths.kb_path, root / "storage" / "users" / "user_123" / "kb" / "knowledge_base.json")
            self.assertEqual(user_paths.doc_cache_dir("sample.pdf"), root / "storage" / "users" / "user_123" / "cache" / "trees" / "sample")


if __name__ == "__main__":
    unittest.main()
