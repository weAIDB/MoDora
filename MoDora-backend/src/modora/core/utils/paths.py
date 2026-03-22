from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modora.core.settings import Settings


@dataclass(frozen=True)
class AppPaths:
    docs_dir: Path
    cache_dir: Path
    log_dir: Path
    storage_root: Path

    @property
    def cache_base(self) -> Path:
        # Trees are stored under cache/trees
        return self.cache_dir / "trees"

    def doc_cache_dir(self, file_name: str) -> Path:
        stem = Path(file_name).stem
        # Directly look for the folder corresponding to the file under the trees directory
        return self.cache_base / stem

    def user_root(self, user_id: str) -> Path:
        return self.storage_root / "users" / user_id

    def user_paths(self, user_id: str) -> "UserPaths":
        root = self.user_root(user_id)
        docs_dir = root / "docs"
        cache_dir = root / "cache"
        kb_dir = root / "kb"
        log_dir = root / "logs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        kb_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        return UserPaths(
            user_id=user_id,
            root=root,
            docs_dir=docs_dir,
            cache_dir=cache_dir,
            kb_dir=kb_dir,
            log_dir=log_dir,
        )


@dataclass(frozen=True)
class UserPaths:
    user_id: str
    root: Path
    docs_dir: Path
    cache_dir: Path
    kb_dir: Path
    log_dir: Path

    @property
    def cache_base(self) -> Path:
        return self.cache_dir / "trees"

    @property
    def kb_path(self) -> Path:
        return self.kb_dir / "knowledge_base.json"

    def doc_cache_dir(self, file_name: str) -> Path:
        stem = Path(file_name).stem
        return self.cache_base / stem


def resolve_paths(settings: Settings) -> AppPaths:
    docs_dir = Path(settings.docs_dir or "").expanduser().resolve()
    cache_dir = Path(settings.cache_dir or "").expanduser().resolve()
    log_dir = Path(settings.log_dir or (cache_dir / "logs")).expanduser().resolve()
    storage_root = Path(settings.storage_root or "").expanduser().resolve()

    docs_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    storage_root.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        docs_dir=docs_dir,
        cache_dir=cache_dir,
        log_dir=log_dir,
        storage_root=storage_root,
    )
