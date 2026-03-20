#!/usr/bin/env python3

from __future__ import annotations

import json
import sys

from common import (
    ensure_absolute_file,
    load_settings_file,
    require_remote_credential_ack,
    upload_file,
)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            f"Usage: {sys.argv[0]} /absolute/path/to/file.pdf --settings-file /path/to/settings.json --allow-remote-credentials\n"
            "Required: skill access must use a user-owned settings file and explicit acknowledgement "
            "before sending credentials to the remote MoDora service."
        )

    file_path = ensure_absolute_file(sys.argv[1])
    settings_file = None
    allow_remote_credentials = False
    if len(sys.argv) >= 4 and sys.argv[2] == "--settings-file":
        settings_file = sys.argv[3]
        extras = sys.argv[4:]
        if extras == ["--allow-remote-credentials"]:
            allow_remote_credentials = True
        elif extras:
            raise SystemExit(
                f"Usage: {sys.argv[0]} /absolute/path/to/file.pdf --settings-file /path/to/settings.json --allow-remote-credentials\n"
                "Required: skill access must use a user-owned settings file and explicit acknowledgement "
                "before sending credentials to the remote MoDora service."
            )
    elif len(sys.argv) > 2:
        raise SystemExit(
            f"Usage: {sys.argv[0]} /absolute/path/to/file.pdf --settings-file /path/to/settings.json --allow-remote-credentials\n"
            "Required: skill access must use a user-owned settings file and explicit acknowledgement "
            "before sending credentials to the remote MoDora service."
        )

    require_remote_credential_ack(allow_remote_credentials)
    settings = load_settings_file(settings_file)
    print(json.dumps(upload_file(file_path, settings), ensure_ascii=False))


if __name__ == "__main__":
    main()
