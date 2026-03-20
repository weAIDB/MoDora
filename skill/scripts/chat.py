#!/usr/bin/env python3

from __future__ import annotations

import json
import sys

from common import chat, load_settings_file, require_remote_credential_ack


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            f'Usage: {sys.argv[0]} <filename> "<question>" --settings-file /path/to/settings.json --allow-remote-credentials\n'
            "Required: skill access must use a user-owned settings file and explicit acknowledgement "
            "before sending credentials to the remote MoDora service."
        )

    settings_file = None
    allow_remote_credentials = False
    if len(sys.argv) >= 5 and sys.argv[3] == "--settings-file":
        settings_file = sys.argv[4]
        extras = sys.argv[5:]
        if extras == ["--allow-remote-credentials"]:
            allow_remote_credentials = True
        elif extras:
            raise SystemExit(
                f'Usage: {sys.argv[0]} <filename> "<question>" --settings-file /path/to/settings.json --allow-remote-credentials\n'
                "Required: skill access must use a user-owned settings file and explicit acknowledgement "
                "before sending credentials to the remote MoDora service."
            )
    elif len(sys.argv) > 3:
        raise SystemExit(
            f'Usage: {sys.argv[0]} <filename> "<question>" --settings-file /path/to/settings.json --allow-remote-credentials\n'
            "Required: skill access must use a user-owned settings file and explicit acknowledgement "
            "before sending credentials to the remote MoDora service."
        )

    require_remote_credential_ack(allow_remote_credentials)
    settings = load_settings_file(settings_file)
    print(json.dumps(chat(sys.argv[1], sys.argv[2], settings), ensure_ascii=False))


if __name__ == "__main__":
    main()
