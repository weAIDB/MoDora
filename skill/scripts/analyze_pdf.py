#!/usr/bin/env python3

from __future__ import annotations

import json
import sys

from common import (
    chat,
    ensure_absolute_file,
    health,
    load_settings_file,
    require_remote_credential_ack,
    upload_file,
    wait_until_completed,
)


def main() -> None:
    if len(sys.argv) < 5 or sys.argv[3] != "--settings-file":
        raise SystemExit(
            f'Usage: {sys.argv[0]} /absolute/path/to/file.pdf "<question>" --settings-file /path/to/settings.json --allow-remote-credentials [timeout_seconds]\n'
            "Required: skill access must use a user-owned settings file and explicit acknowledgement "
            "before sending credentials to the remote MoDora service."
        )

    file_path = ensure_absolute_file(sys.argv[1])
    question = sys.argv[2]
    settings = load_settings_file(sys.argv[4])
    extras = sys.argv[5:]
    allow_remote_credentials = False
    timeout_seconds = 600
    if extras:
        if extras[0] == "--allow-remote-credentials":
            allow_remote_credentials = True
            if len(extras) >= 2:
                timeout_seconds = int(extras[1])
            if len(extras) > 2:
                raise SystemExit(
                    f'Usage: {sys.argv[0]} /absolute/path/to/file.pdf "<question>" --settings-file /path/to/settings.json --allow-remote-credentials [timeout_seconds]'
                )
        else:
            raise SystemExit(
                f'Usage: {sys.argv[0]} /absolute/path/to/file.pdf "<question>" --settings-file /path/to/settings.json --allow-remote-credentials [timeout_seconds]'
            )

    require_remote_credential_ack(allow_remote_credentials)
    health()
    upload_file(file_path, settings)
    wait_until_completed(file_path.name, timeout_seconds)
    print(json.dumps(chat(file_path.name, question, settings), ensure_ascii=False))


if __name__ == "__main__":
    main()
