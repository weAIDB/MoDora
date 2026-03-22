from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import Response

from modora.api.auth import AuthRequest, register
from modora.api.v1.conversations import (
    create_conversation_endpoint,
    delete_conversation_endpoint,
    list_conversations,
    update_conversation_endpoint,
)
from modora.api.v1.models import ConversationCreateRequest, ConversationMessageItem, ConversationUpdateRequest
from modora.core.persistence import init_db
from modora.core.persistence.documents import create_document
from modora.core.settings import Settings


class ConversationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "service_name": "modora-conv-test",
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
            AuthRequest(email="conv@example.com", password="conv-pass-123"),
            response=Response(),
            settings=self.settings,
        ).user
        self.document = create_document(
            self.settings,
            user_id=self.user.id,
            original_name="sample.pdf",
            storage_key="doc_123_sample.pdf",
        )

    def tearDown(self) -> None:
        if self.old_config is None:
            os.environ.pop("MODORA_CONFIG", None)
        else:
            os.environ["MODORA_CONFIG"] = self.old_config
        self.tmpdir.cleanup()

    def test_conversation_crud(self) -> None:
        created = create_conversation_endpoint(
            ConversationCreateRequest(title="Research Session"),
            user=self.user,
        )
        self.assertEqual(created.title, "Research Session")

        updated = update_conversation_endpoint(
            created.id,
            ConversationUpdateRequest(
                title="Updated Session",
                document_ids=[self.document.id],
                messages=[
                    ConversationMessageItem(role="user", content="hello", citations=[]),
                    ConversationMessageItem(role="assistant", content="world", citations=[]),
                ],
            ),
            user=self.user,
        )
        self.assertEqual(updated.title, "Updated Session")
        self.assertEqual(len(updated.documents), 1)
        self.assertEqual(updated.documents[0].id, self.document.id)
        self.assertEqual(len(updated.messages), 2)

        listed = list_conversations(user=self.user)
        self.assertEqual(len(listed.conversations), 1)
        self.assertEqual(listed.conversations[0].id, created.id)

        delete_conversation_endpoint(created.id, user=self.user)
        listed_after_delete = list_conversations(user=self.user)
        self.assertEqual(len(listed_after_delete.conversations), 0)


if __name__ == "__main__":
    unittest.main()
