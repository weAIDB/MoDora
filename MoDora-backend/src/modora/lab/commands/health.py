from __future__ import annotations

import argparse
import logging


def register(sub: argparse._SubParsersAction) -> None:
    """Register the health subcommand.

    Args:
        sub: The sub-parsers action to add the parser to.
    """
    p = sub.add_parser("health", help="Check health status")
    p.set_defaults(_handler=_handle_health)


def _handle_health(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Handler for the health command to check system status.

    Args:
        args: Command-line arguments.
        logger: Logger instance.

    Returns:
        Exit code (always 0).
    """
    logger.info("ok")
    return 0
