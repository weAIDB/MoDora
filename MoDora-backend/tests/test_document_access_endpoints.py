from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, Response

from modora.api.auth import AuthRequest, register
from modora.api.v1.documents import upload_file
from modora.api.v1.documents import get_document_file
from modora.api.v1.kb import delete_kb_doc_by_document_id, get_kb_docs, update_kb_doc_tags
from modora.api.v1.models import UpdateTagsRequest
from modora.api.v1.stats import get_doc_stats_by_document_id
from modora.api.v1.models import TreeRequest
from modora.api.v1.tree import get_document_tree
from modora.core.persistence import init_db
from modora.core.persistence.documents import get_document_by_id
from modora.core.services.kb import KnowledgeBaseManager
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        if size is None or size < 0:
            size = len(self._content) - self._offset
        start = self._offset
        end = min(len(self._content), start + size)
        self._offset = end
        return self._content[start:end]

    async def close(self) -> None:
        return None


class DocumentAccessEndpointsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "service_name": "modora-access-test",
                    "docs_dir": str(root / "docs"),
                    "cache_dir": str(root / "cache"),
                    "storage_root": str(root / "storage"),
                    "db_path": str(root / "storage" / "modora.db"),
                    "cors_allowed_origins": ["https://modora.pro"],
                    "ocr_model": "disabled",
                    "enable_ocr_preload": False,
                    "enable_vector_search": False,
                    "model_instances": {},
                    "auth_session_cookie_name": "modora_session",
                }
            ),
            encoding="utf-8",
        )
        self.old_config = os.environ.get("MODORA_CONFIG")
        os.environ["MODORA_CONFIG"] = str(self.config_path)
        self.settings = Settings.load(str(self.config_path))
        init_db(self.settings)
        self.user = register(
            AuthRequest(email="access@example.com", password="access-pass-123"),
            response=Response(),
            settings=self.settings,
        ).user

        result = asyncio.run(
            upload_file(
                background_tasks=BackgroundTasks(),
                file=FakeUploadFile("sample.pdf", b"%PDF-1.4\n%smoke\n"),
                settings=None,
                user=self.user,
            )
        )
        assert result.document_id is not None
        self.document_id = result.document_id
        self.document = get_document_by_id(
            self.settings,
            user_id=self.user.id,
            document_id=self.document_id,
        )
        assert self.document is not None

        user_paths = resolve_paths(self.settings).user_paths(self.user.id)
        cache_dir = user_paths.doc_cache_dir(self.document.storage_key)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "ocr.json").write_text(
            json.dumps(
                {
                    "blocks": [
                        {"label": "text", "page_id": 1},
                        {"label": "image", "page_id": 1},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (cache_dir / "tree.json").write_text(
            json.dumps(
                {
                    "title": self.document.original_name,
                    "type": "section",
                    "children": {
                        "Intro": {
                            "title": "Intro",
                            "type": "text",
                            "children": {},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        kb = KnowledgeBaseManager(user_paths.kb_path)
        kb.update_doc_info(
            self.document.storage_key,
            {
                "tags": ["alpha"],
                "semantic_tags": ["beta"],
            },
        )

    def tearDown(self) -> None:
        if self.old_config is None:
            os.environ.pop("MODORA_CONFIG", None)
        else:
            os.environ["MODORA_CONFIG"] = self.old_config
        self.tmpdir.cleanup()

    def test_stats_and_kb_use_document_id_with_user_scope(self) -> None:
        stats = asyncio.run(
            get_doc_stats_by_document_id(self.document_id, user=self.user)
        )
        self.assertEqual(stats.pages, 1)
        self.assertEqual(stats.counts["text"], 1)
        self.assertEqual(stats.counts["image"], 1)
        self.assertEqual(stats.tags, ["alpha"])
        self.assertEqual(stats.semantic_tags, ["beta"])

        update_kb_doc_tags(
            UpdateTagsRequest(document_id=self.document_id, tags=["reviewed"]),
            user=self.user,
        )
        docs = get_kb_docs(user=self.user)
        self.assertIn(self.document.storage_key, docs)
        self.assertEqual(docs[self.document.storage_key]["tags"], ["reviewed"])

    def test_delete_by_document_id_removes_file_cache_and_record(self) -> None:
        user_paths = resolve_paths(self.settings).user_paths(self.user.id)
        source_path = user_paths.docs_dir / self.document.storage_key
        cache_dir = user_paths.doc_cache_dir(self.document.storage_key)
        self.assertTrue(source_path.exists())
        self.assertTrue(cache_dir.exists())

        with patch("modora.api.v1.kb.delete_source_index") as delete_index:
            result = delete_kb_doc_by_document_id(self.document_id, user=self.user)

        self.assertEqual(result["status"], "success")
        delete_index.assert_called_once_with(
            self.settings,
            source_path=str(source_path),
        )
        self.assertFalse(source_path.exists())
        self.assertFalse(cache_dir.exists())
        self.assertIsNone(
            get_document_by_id(
                self.settings,
                user_id=self.user.id,
                document_id=self.document_id,
            )
        )

    def test_tree_and_pdf_file_access_use_authenticated_document_scope(self) -> None:
        tree = asyncio.run(
            get_document_tree(
                TreeRequest(
                    file_name=self.document.original_name,
                    document_id=self.document_id,
                ),
                user=self.user,
            )
        )
        self.assertTrue(len(tree.elements) > 0)

        response = get_document_file(self.document_id, user=self.user)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn(self.document.storage_key, str(response.path))


if __name__ == "__main__":
    unittest.main()
