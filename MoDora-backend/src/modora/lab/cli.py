from __future__ import annotations

import argparse
import logging

from modora.core.logging_context import new_id, run_scope
from modora.core.logging_setup import configure_logging
from modora.core.settings import Settings

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modora")
    parser.add_argument("--config", default=None)
    parser.add_argument("--run-id", default=None)

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")

    args = parser.parse_args(argv)

    settings = Settings.load(args.config)
    configure_logging(settings)
    logger = logging.getLogger("modora.lab")

    run_id = args.run_id or new_id("run_", 8)
    with run_scope(run_id):
        if args.cmd == "health":
            logger.info("ok")
            return 0
    return 0

if __name__ == "__main__":
    raise SystemExit(main())