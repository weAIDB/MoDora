from __future__ import annotations

import threading
from typing import Dict


class TaskStatusStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, str] = {}

    def _key(self, filename: str, user_id: str | None = None) -> str:
        if user_id:
            return f"{user_id}:{filename}"
        return filename

    def set(self, filename: str, status: str) -> None:
        with self._lock:
            self._store[self._key(filename)] = status

    def get(self, filename: str) -> str:
        with self._lock:
            return self._store.get(self._key(filename), "unknown")

    def set_for_user(self, user_id: str, filename: str, status: str) -> None:
        with self._lock:
            self._store[self._key(filename, user_id=user_id)] = status

    def get_for_user(self, user_id: str, filename: str) -> str:
        with self._lock:
            return self._store.get(self._key(filename, user_id=user_id), "unknown")


TASK_STATUS = TaskStatusStore()
