#!/usr/bin/env python3

from __future__ import annotations

import sys

from common import wait_until_completed


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            f"Usage: {sys.argv[0]} <filename> [timeout_seconds] [poll_interval_seconds]"
        )

    filename = sys.argv[1]
    timeout_seconds = int(sys.argv[2]) if len(sys.argv) >= 3 else 600
    poll_interval = float(sys.argv[3]) if len(sys.argv) >= 4 else 2.0
    wait_until_completed(filename, timeout_seconds, poll_interval)


if __name__ == "__main__":
    main()
