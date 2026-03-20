#!/usr/bin/env python3

from __future__ import annotations

import json

from common import health


def main() -> None:
    print(json.dumps(health(), ensure_ascii=False))


if __name__ == "__main__":
    main()
