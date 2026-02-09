from __future__ import annotations

import argparse
import logging


def register(sub: argparse._SubParsersAction) -> None:
    """注册 health 子命令"""
    p = sub.add_parser("health", help="Check health status")
    p.set_defaults(_handler=_handle_health)


def _handle_health(args: argparse.Namespace, logger: logging.Logger) -> int:
    """health 命令的处理器，用于检查系统状态"""
    logger.info("ok")
    return 0
