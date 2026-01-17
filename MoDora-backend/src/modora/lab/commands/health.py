from __future__ import annotations

import argparse
import logging


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("health", help="Check health status")
    p.set_defaults(_handler=_handle_health)


def _handle_health(args: argparse.Namespace, logger: logging.Logger) -> int:
    logger.info("ok")
    return 0
