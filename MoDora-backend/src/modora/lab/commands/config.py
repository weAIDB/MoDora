from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict

from modora.core.settings import Settings


def register(sub: argparse._SubParsersAction) -> None:
    """Register the config-show subcommand.

    Args:
        sub: The sub-parsers action to add the parser to.
    """
    p = sub.add_parser("config-show", help="Show current effective configuration")
    p.add_argument("--json", action="store_true", help="Output in JSON format")
    p.add_argument("--show-secrets", action="store_true", help="Show secret fields")
    p.set_defaults(_handler=_handle_config_show)


def _handle_config_show(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Handler for the config-show command to display the currently active configuration.

    Args:
        args: Command-line arguments.
        logger: Logger instance.

    Returns:
        Exit code (always 0).
    """
    settings = Settings.load()
    data = asdict(settings)
    # Hide API keys by default
    if not getattr(args, "show_secrets", False):
        if data.get("api_key"):
            data["api_key"] = "sk-******"
    config_path = (
        getattr(args, "config", None) or os.getenv("MODORA_CONFIG") or ""
    ).strip()
    config_path = config_path or None
    payload = {"config_path": config_path, "settings": data}
    # Print configuration information in JSON format
    print(json.dumps(payload, ensure_ascii=False, indent=4))
    logger.info("printed config", extra={"config_path": config_path})
    return 0
