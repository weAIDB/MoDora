from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modora.core.settings import Settings


@dataclass(frozen=True)
class AppPaths:
    docs_dir: Path
    cache_dir: Path
    log_dir: Path

    @property
    def cache_base(self) -> Path:
        return self.cache_dir / self.docs_dir.name

    def doc_cache_dir(self, file_name: str) -> Path:
        stem = Path(file_name).stem
        return self.cache_base / stem


def resolve_paths(settings: Settings) -> AppPaths:
    docs_dir = Path(settings.docs_dir or "").expanduser().resolve()
    cache_dir = Path(settings.cache_dir or "").expanduser().resolve()
    log_dir = Path(settings.log_dir or (cache_dir / "logs")).expanduser().resolve()

    docs_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    return AppPaths(docs_dir=docs_dir, cache_dir=cache_dir, log_dir=log_dir)
