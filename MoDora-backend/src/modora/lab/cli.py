from __future__ import annotations

import argparse
import logging

from modora.core.infra.logging.context import new_id, run_scope
from modora.core.infra.logging.setup import configure_logging
from modora.core.settings import Settings
from modora.lab.commands import (
    register_build_tree,
    register_batch_qa,
    register_config,
    register_evaluate,
    register_health,
    register_preprocess,
    register_qa
)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modora")
    parser.add_argument("--config", default=None)
    parser.add_argument("--run-id", default=None)

    sub = parser.add_subparsers(dest="cmd", required=True)

    register_build_tree(sub)
    register_health(sub)
    register_config(sub)
    register_qa(sub)
    register_batch_qa(sub)
    register_evaluate(sub)
    register_preprocess(sub)

    args = parser.parse_args(argv)

    settings = Settings.load(args.config)
    configure_logging(settings)
    logger = logging.getLogger("modora.lab")

    run_id = args.run_id or new_id("run_", 8)
    with run_scope(run_id):
        handler = getattr(args, "_handler", None)
        if handler is None:
            logger.error("no handler for command", extra={"cmd": args.cmd})
            return 2
        return int(handler(args, logger))


if __name__ == "__main__":
    raise SystemExit(main())
