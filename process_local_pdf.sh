#!/bin/bash

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <filename> [settings_b64]" >&2
    exit 1
fi

FILE_NAME="$1"
SETTINGS_B64="${2:-}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_ROOT/MoDora-backend"

if [ ! -d "venv" ]; then
    echo "Missing backend virtualenv: $PROJECT_ROOT/MoDora-backend/venv" >&2
    exit 1
fi

source venv/bin/activate

if [ -f "../local.json" ]; then
    export MODORA_CONFIG="../local.json"
fi

PYTHONPATH=src python - "$FILE_NAME" "$SETTINGS_B64" <<'PY'
import asyncio
import base64
import json
import logging
import sys
from pathlib import Path

from modora.core.services.document_processing import process_document_task
from modora.core.settings import Settings
from modora.core.utils.paths import resolve_paths


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("filename is required")

    filename = Path(sys.argv[1]).name
    settings_b64 = sys.argv[2] if len(sys.argv) > 2 else ""

    cfg = None
    if settings_b64:
        try:
            cfg = json.loads(base64.b64decode(settings_b64).decode("utf-8"))
        except Exception:
            cfg = None

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("modora.manual_upload")

    settings = Settings.load()
    paths = resolve_paths(settings)
    source_path = paths.docs_dir / filename
    if not source_path.exists():
        raise SystemExit(f"file not found: {source_path}")

    asyncio.run(
        process_document_task(
            str(source_path),
            paths,
            settings,
            cfg,
            logger,
        )
    )


if __name__ == "__main__":
    main()
PY
