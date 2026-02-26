from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KnowledgeBaseManager:
    def __init__(self, kb_path: Path):
        self.kb_path = kb_path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.kb_path.exists():
            self.kb_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"docs": {}, "tag_library": []}
            self._save(data)
            return data

        try:
            return json.loads(self.kb_path.read_text(encoding="utf-8"))
        except Exception:
            return {"docs": {}, "tag_library": []}

    def _save(self, data: dict[str, Any] | None = None) -> None:
        payload = data if data is not None else self.data
        self.kb_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def update_doc_info(self, file_name: str, info: dict[str, Any]) -> None:
        if file_name not in self.data["docs"]:
            self.data["docs"][file_name] = {
                "tags": [],
                "semantic_tags": [],
                "stats": {},
                "added_at": None,
            }

        self.data["docs"][file_name].update(info)

        all_tags = set(self.data["tag_library"])
        tags = info.get("tags") or []
        semantic = info.get("semantic_tags") or []
        all_tags.update(tags)
        all_tags.update(semantic)
        self.data["tag_library"] = sorted(all_tags)
        self._save()

    def get_doc_info(self, file_name: str) -> dict[str, Any] | None:
        return self.data["docs"].get(file_name)

    def get_all_docs(self) -> dict[str, Any]:
        return self.data["docs"]

    def get_tag_library(self) -> list[str]:
        return self.data["tag_library"]

    def delete_tag_from_library(self, tag: str) -> None:
        if tag not in self.data["tag_library"]:
            return
        self.data["tag_library"].remove(tag)
        for doc in self.data["docs"].values():
            if tag in doc.get("tags", []):
                doc["tags"].remove(tag)
            if tag in doc.get("semantic_tags", []):
                doc["semantic_tags"].remove(tag)
        self._save()

    def delete_doc(self, file_name: str) -> None:
        if file_name in self.data["docs"]:
            del self.data["docs"][file_name]
            self._save()

    def update_doc_tags(self, file_name: str, tags: list[str]) -> None:
        if file_name not in self.data["docs"]:
            return
        self.data["docs"][file_name]["tags"] = tags
        self.data["docs"][file_name]["semantic_tags"] = []
        all_tags = set(self.data["tag_library"])
        all_tags.update(tags)
        self.data["tag_library"] = sorted(all_tags)
        self._save()
