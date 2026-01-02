import os
import json
from typing import List, Dict, Any, Optional

CACHE_DIR = "cache"

class KnowledgeBaseManager:
    def __init__(self):
        self.kb_path = os.path.join(CACHE_DIR, "knowledge_base.json")
        self.data = self._load_kb()

    def _load_kb(self) -> Dict[str, Any]:
        if not os.path.exists(self.kb_path):
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
            default_data = {"docs": {}, "tag_library": []}
            self._save_kb(default_data)
            return default_data
        
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading KB: {e}")
            return {"docs": {}, "tag_library": []}

    def _save_kb(self, data: Optional[Dict] = None):
        if data is None:
            data = self.data
        try:
            with open(self.kb_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving KB: {e}")

    def update_doc_info(self, file_name: str, info: Dict):
        """Update or add document info in KB"""
        if file_name not in self.data["docs"]:
            self.data["docs"][file_name] = {
                "tags": [],
                "semantic_tags": [],
                "stats": {},
                "added_at": None
            }
        
        self.data["docs"][file_name].update(info)
        
        # Update tag library
        all_tags = set(self.data["tag_library"])
        if "tags" in info:
            all_tags.update(info["tags"])
        if "semantic_tags" in info:
            all_tags.update(info["semantic_tags"])
        
        self.data["tag_library"] = sorted(list(all_tags))
        self._save_kb()

    def get_doc_info(self, file_name: str) -> Optional[Dict]:
        return self.data["docs"].get(file_name)

    def get_all_docs(self) -> Dict:
        return self.data["docs"]

    def get_tag_library(self) -> List[str]:
        return self.data["tag_library"]

    def delete_tag_from_library(self, tag: str):
        if tag in self.data["tag_library"]:
            self.data["tag_library"].remove(tag)
            # Remove tag from all documents
            for doc_name in self.data["docs"]:
                doc = self.data["docs"][doc_name]
                if tag in doc.get("tags", []):
                    doc["tags"].remove(tag)
                if tag in doc.get("semantic_tags", []):
                    doc["semantic_tags"].remove(tag)
            self._save_kb()

    def update_doc_tags(self, file_name: str, tags: List[str]):
        if file_name in self.data["docs"]:
            # 当用户手动编辑标签时，我们将其全部存入 tags，并清空 semantic_tags
            # 这样用户的手动干预就成为了最终结果
            self.data["docs"][file_name]["tags"] = tags
            self.data["docs"][file_name]["semantic_tags"] = []
            
            # 更新全局标签库
            all_tags = set(self.data["tag_library"])
            all_tags.update(tags)
            self.data["tag_library"] = sorted(list(all_tags))
            self._save_kb()

kb_manager = KnowledgeBaseManager()
