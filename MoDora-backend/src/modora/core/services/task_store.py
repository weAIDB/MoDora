from __future__ import annotations

import threading
from typing import Dict


class TaskStatusStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, str] = {}

    def set(self, filename: str, status: str) -> None:
        with self._lock:
            self._store[filename] = status

    def get(self, filename: str) -> str:
        with self._lock:
            return self._store.get(filename, "unknown")


TASK_STATUS = TaskStatusStore()
