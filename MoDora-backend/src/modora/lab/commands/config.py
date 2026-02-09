from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict

from modora.core.settings import Settings


def register(sub: argparse._SubParsersAction) -> None:
    """注册 config-show 子命令"""
    p = sub.add_parser("config-show", help="Show current effective configuration")
    p.add_argument("--json", action="store_true", help="Output in JSON format")
    p.add_argument("--show-secrets", action="store_true", help="Show secret fields")
    p.set_defaults(_handler=_handle_config_show)


def _handle_config_show(args: argparse.Namespace, logger: logging.Logger) -> int:
    """config-show 命令的处理器，用于显示当前生效的配置"""
    settings = Settings.load()
    data = asdict(settings)
    # 默认隐藏 API Key
    if not getattr(args, "show_secrets", False):
        if data.get("api_key"):
            data["api_key"] = "sk-******"
    config_path = (
        getattr(args, "config", None) or os.getenv("MODORA_CONFIG") or ""
    ).strip()
    config_path = config_path or None
    payload = {"config_path": config_path, "settings": data}
    # 打印 JSON 格式的配置信息
    print(json.dumps(payload, ensure_ascii=False, indent=4))
    logger.info("printed config", extra={"config_path": config_path})
    return 0
