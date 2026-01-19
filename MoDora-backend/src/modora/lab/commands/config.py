from __future__ import annotations

import argparse
import configparser
import json
import logging
import os
from dataclasses import asdict

from modora.core.settings import Settings

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("config-show", help="Show current effective configuration")
    p.add_argument("--json", action="store_true", help="Output in JSON format")
    p.add_argument("--show-secrets", action="store_true", help="Show secret fields")
    p.set_defaults(_handler=_handle_config_show)

def _handle_config_show(args: argparse.Namespace, logger: logging.Logger) -> int:
    settings = Settings.load()
    data = asdict(settings)
    if not getattr(args, "show_secrets", False):
        if data.get("api_key"):
            data["api_key"] = "sk-******"
    config_path = (getattr(args, "config", None) or os.getenv("MODORA_CONFIG") or "").strip() 
    config_path = config_path or None
    payload = {
        "config_path": config_path,
        "settings": data
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))
    logger.info("printed config", extra={"config_path": config_path})
    return 0
