from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, Response

from modora.api.auth import AuthRequest, register
from modora.api.v1.model_instances import (
    CreateModelInstanceRequest,
    create_model_instance,
    delete_model_instance,
    get_ui_settings,
    list_model_instances,
    update_ui_settings,
)
from modora.core.persistence import init_db
from modora.core.persistence.user_preferences import effective_settings_for_user
from modora.core.settings import Settings
from modora.core.utils.config import settings_from_ui_payload


class UserModelInstancesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "service_name": "modora-model-settings-test",
                    "docs_dir": str(root / "docs"),
                    "cache_dir": str(root / "cache"),
                    "storage_root": str(root / "storage"),
                    "db_path": str(root / "storage" / "modora.db"),
                    "auth_session_cookie_name": "modora_session",
                    "model_instances": {
                        "remote-default": {
                            "type": "remote",
                            "model": "default-model",
                            "base_url": "https://default.example.com/v1",
                            "api_key": "default-key",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        self.old_config = os.environ.get("MODORA_CONFIG")
        os.environ["MODORA_CONFIG"] = str(self.config_path)
        self.settings = Settings.load(str(self.config_path))
        init_db(self.settings)
        self.user_a = register(
            AuthRequest(email="user-a@example.com", password="secret-123"),
            response=Response(),
            settings=self.settings,
        ).user
        self.user_b = register(
            AuthRequest(email="user-b@example.com", password="secret-456"),
            response=Response(),
            settings=self.settings,
        ).user

    def tearDown(self) -> None:
        if self.old_config is None:
            os.environ.pop("MODORA_CONFIG", None)
        else:
            os.environ["MODORA_CONFIG"] = self.old_config
        self.tmpdir.cleanup()

    def test_user_model_instances_are_isolated_and_resolvable(self) -> None:
        created = create_model_instance(
            CreateModelInstanceRequest(
                model_name="gpt-4.1",
                base_url="https://user-a.example.com/v1",
                api_key="user-a-key",
            ),
            user=self.user_a,
        )
        self.assertEqual(created["instance"]["id"], "gpt-4.1")

        instances_a = list_model_instances(user=self.user_a)["instances"]
        ids_a = {item["id"] for item in instances_a}
        self.assertIn("gpt-4.1", ids_a)

        instances_b = list_model_instances(user=self.user_b)["instances"]
        ids_b = {item["id"] for item in instances_b}
        self.assertEqual(ids_b, set())
        self.assertNotIn("gpt-4.1", ids_b)

        saved = update_ui_settings(
            {
                "settings": {
                    "schemaVersion": 3,
                    "ocr": {"provider": "ppstructure"},
                    "pipelines": {
                        "qaService": {"modelInstance": "gpt-4.1"},
                    },
                }
            },
            user=self.user_a,
        )
        self.assertEqual(
            saved["settings"]["pipelines"]["qaService"]["modelInstance"], "gpt-4.1"
        )

        loaded = get_ui_settings(user=self.user_a)
        self.assertEqual(
            loaded["settings"]["pipelines"]["qaService"]["modelInstance"], "gpt-4.1"
        )

        effective = effective_settings_for_user(Settings.load(), user_id=self.user_a.id)
        qa_settings, _, instance_id, _ = settings_from_ui_payload(
            effective,
            loaded["settings"],
            module_key="qaService",
        )
        self.assertEqual(instance_id, "gpt-4.1")
        resolved = qa_settings.resolve_model_instance(instance_id)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.model, "gpt-4.1")
        self.assertEqual(resolved.base_url, "https://user-a.example.com/v1")

    def test_duplicate_model_name_is_rejected_per_user(self) -> None:
        create_model_instance(
            CreateModelInstanceRequest(
                model_name="gpt-4.1",
                base_url="https://user-a.example.com/v1",
                api_key="user-a-key",
            ),
            user=self.user_a,
        )

        with self.assertRaises(HTTPException) as ctx:
            create_model_instance(
                CreateModelInstanceRequest(
                    model_name="gpt-4.1",
                    base_url="https://user-a.example.com/other",
                    api_key="other-key",
                ),
                user=self.user_a,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already exists", str(ctx.exception.detail))

    def test_delete_model_instance_requires_it_to_be_unused(self) -> None:
        create_model_instance(
            CreateModelInstanceRequest(
                model_name="gpt-4.1",
                base_url="https://user-a.example.com/v1",
                api_key="user-a-key",
            ),
            user=self.user_a,
        )
        update_ui_settings(
            {
                "settings": {
                    "schemaVersion": 3,
                    "ocr": {"provider": "ppstructure"},
                    "pipelines": {
                        "qaService": {"modelInstance": "gpt-4.1"},
                    },
                }
            },
            user=self.user_a,
        )

        with self.assertRaises(HTTPException) as ctx:
            delete_model_instance("gpt-4.1", user=self.user_a)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("still referenced", str(ctx.exception.detail))

        update_ui_settings(
            {
                "settings": {
                    "schemaVersion": 3,
                    "ocr": {"provider": "ppstructure"},
                    "pipelines": {
                        "qaService": {},
                        "retriever": {},
                    },
                }
            },
            user=self.user_a,
        )
        delete_model_instance("gpt-4.1", user=self.user_a)
        ids = {item["id"] for item in list_model_instances(user=self.user_a)["instances"]}
        self.assertNotIn("gpt-4.1", ids)


if __name__ == "__main__":
    unittest.main()
