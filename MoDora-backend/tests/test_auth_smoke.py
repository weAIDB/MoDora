from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import Response
from fastapi import HTTPException
from starlette.requests import Request

from modora.api.auth import AuthRequest, login, logout, register
from modora.core.auth.service import get_user_by_session
from modora.core.persistence import init_db
from modora.core.settings import Settings


def _extract_cookie_value(set_cookie_header: str, key: str) -> str:
    for part in set_cookie_header.split(";"):
        item = part.strip()
        if item.startswith(f"{key}="):
            return item.split("=", 1)[1]
    raise AssertionError(f"cookie {key} not found in header: {set_cookie_header}")


def _request_with_cookie(cookie_name: str, cookie_value: str) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/auth/logout",
            "raw_path": b"/api/auth/logout",
            "query_string": b"",
            "headers": [(b"cookie", f"{cookie_name}={cookie_value}".encode("utf-8"))],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
        }
    )


class AuthSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.config_path = root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "service_name": "modora-auth-test",
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

    def tearDown(self) -> None:
        if self.old_config is None:
            os.environ.pop("MODORA_CONFIG", None)
        else:
            os.environ["MODORA_CONFIG"] = self.old_config
        self.tmpdir.cleanup()

    def test_register_login_logout_flow(self) -> None:
        email = "smoke@example.com"
        password = "smoke-pass-123"

        register_response = Response()
        register_result = register(
            AuthRequest(email=email, password=password),
            register_response,
            self.settings,
        )
        self.assertEqual(register_result.user.email, email)
        set_cookie_header = register_response.headers.get("set-cookie", "")
        self.assertIn(self.settings.auth_session_cookie_name, set_cookie_header)
        register_session_id = _extract_cookie_value(
            set_cookie_header, self.settings.auth_session_cookie_name
        )
        current_user = get_user_by_session(self.settings, register_session_id)
        self.assertIsNotNone(current_user)
        self.assertEqual(current_user.email, email)

        login_response = Response()
        login_result = login(
            AuthRequest(email=email, password=password),
            login_response,
            self.settings,
        )
        self.assertEqual(login_result.user.email, email)
        login_cookie_header = login_response.headers.get("set-cookie", "")
        login_session_id = _extract_cookie_value(
            login_cookie_header, self.settings.auth_session_cookie_name
        )
        self.assertIsNotNone(get_user_by_session(self.settings, login_session_id))

        logout_request = _request_with_cookie(
            self.settings.auth_session_cookie_name,
            login_session_id,
        )
        logout_response = Response()
        result = logout(logout_request, logout_response, self.settings)
        self.assertEqual(result.status_code, 204)
        self.assertIsNone(get_user_by_session(self.settings, login_session_id))

    def test_duplicate_registration_is_rejected(self) -> None:
        payload = AuthRequest(email="dup@example.com", password="duplicate-123")
        first = register(payload, Response(), self.settings)
        self.assertEqual(first.user.email, "dup@example.com")

        with self.assertRaises(HTTPException) as ctx:
            register(payload, Response(), self.settings)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("email already registered", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
