from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import BackgroundTasks, Response

from modora.api.auth import AuthRequest, register
from modora.api.v1.documents import get_task_status, list_documents, upload_file
from modora.core.persistence.documents import get_document_by_id, get_job_by_id
from modora.core.persistence import init_db
from modora.core.settings import Settings


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


class DocumentJobFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "service_name": "modora-doc-test",
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
            AuthRequest(email="doc@example.com", password="doc-pass-123"),
            response=Response(),
            settings=self.settings,
        ).user

    def tearDown(self) -> None:
        if self.old_config is None:
            os.environ.pop("MODORA_CONFIG", None)
        else:
            os.environ["MODORA_CONFIG"] = self.old_config
        self.tmpdir.cleanup()

    def test_authenticated_upload_creates_document_and_job_records(self) -> None:
        background = BackgroundTasks()
        upload = FakeUploadFile(
            filename="sample.pdf",
            content=b"%PDF-1.4\n%smoke\n",
        )

        result = asyncio.run(
            upload_file(
                background_tasks=background,
                file=upload,
                settings=None,
                user=self.user,
            )
        )

        self.assertIsNotNone(result.document_id)
        self.assertIsNotNone(result.job_id)
        self.assertEqual(result.filename, "sample.pdf")
        self.assertEqual(len(background.tasks), 1)

        doc = get_document_by_id(
            self.settings,
            user_id=self.user.id,
            document_id=result.document_id,
        )
        self.assertIsNotNone(doc)
        assert doc is not None
        self.assertEqual(doc.original_name, "sample.pdf")
        self.assertEqual(doc.status, "pending")
        self.assertTrue(doc.storage_key.startswith(f"{doc.id}_"))

        job = get_job_by_id(
            self.settings,
            user_id=self.user.id,
            job_id=result.job_id,
        )
        self.assertIsNotNone(job)
        assert job is not None
        self.assertEqual(job.document_id, doc.id)
        self.assertEqual(job.status, "pending")

        saved_file = Path(self.settings.storage_root) / "users" / self.user.id / "docs" / doc.storage_key
        self.assertTrue(saved_file.exists())

        status = get_task_status(result.job_id, user=self.user)
        self.assertEqual(status.status, "pending")
        self.assertEqual(status.document_id, doc.id)
        self.assertEqual(status.job_id, job.id)

        documents = list_documents(user=self.user)
        self.assertEqual(len(documents.documents), 1)
        self.assertEqual(documents.documents[0].id, doc.id)


if __name__ == "__main__":
    unittest.main()
