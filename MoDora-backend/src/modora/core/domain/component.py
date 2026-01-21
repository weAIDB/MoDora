from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TITLE = "Default Title"


@dataclass(slots=True)
class Location:
    """组件在 PDF 上的定位信息。page 从 1 开始，bbox 为 [x0, y0, x1, y1]。"""

    bbox: list[float]
    page: int

    def to_dict(self) -> dict[str, Any]:
        return {"bbox": list(self.bbox), "page": int(self.page)}

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Location":
        bbox = obj.get("bbox")
        page = obj.get("page")
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        bbox_f = [float(x) for x in bbox[:4]]
        return Location(bbox=bbox_f, page=int(page or 0))


@dataclass(slots=True)
class Component:
    """预处理阶段抽取出的组件（text/image/chart/table/header/footer...）。"""

    type: str
    title: str = TITLE
    metadata: Any | None = None
    data: str = ""
    location: list[Location] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Component":
        locs: list[Location] = []
        raw_locs = obj.get("location")
        if isinstance(raw_locs, list):
            for it in raw_locs:
                if isinstance(it, dict):
                    locs.append(Location.from_dict(it))
        return Component(
            type=str(obj.get("type") or ""),
            title=str(obj.get("title") or TITLE),
            metadata=obj.get("metadata"),
            data=str(obj.get("data") or ""),
            location=locs,
        )


@dataclass(slots=True)
class Supplement:
    """页眉/页脚/页码/边栏等补充信息，按页号聚合。"""

    header: dict[int, Component] = field(default_factory=dict)
    footer: dict[int, Component] = field(default_factory=dict)
    number: dict[int, Component] = field(default_factory=dict)
    aside: dict[int, Component] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def dump_map(m: dict[int, Component]) -> dict[str, Any]:
            out: dict[str, Any] = {}
            for k, v in m.items():
                out[str(int(k))] = v.to_dict()
            return out

        return {
            "header": dump_map(self.header),
            "footer": dump_map(self.footer),
            "number": dump_map(self.number),
            "aside": dump_map(self.aside),
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Supplement":
        def load_map(x: Any) -> dict[int, Component]:
            out: dict[int, Component] = {}
            if not isinstance(x, dict):
                return out
            for k, v in x.items():
                try:
                    ki = int(k)
                except Exception:
                    continue
                if isinstance(v, dict):
                    out[ki] = Component.from_dict(v)
            return out

        return Supplement(
            header=load_map(obj.get("header")),
            footer=load_map(obj.get("footer")),
            number=load_map(obj.get("number")),
            aside=load_map(obj.get("aside")),
        )


@dataclass(slots=True)
class ComponentPack:
    """整份文档的组件集合：正文 body + 补充信息 supplement。"""

    body: list[Component] = field(default_factory=list)
    supplement: Supplement = field(default_factory=Supplement)

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": [co.to_dict() for co in self.body],
            "supplement": self.supplement.to_dict(),
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "ComponentPack":
        body: list[Component] = []
        raw_body = obj.get("body")
        if isinstance(raw_body, list):
            for it in raw_body:
                if isinstance(it, dict):
                    body.append(Component.from_dict(it))
        supp_obj = obj.get("supplement")
        supp = (
            Supplement.from_dict(supp_obj)
            if isinstance(supp_obj, dict)
            else Supplement()
        )
        return ComponentPack(body=body, supplement=supp)

    def save_json(self, path: str) -> None:
        """将 ComponentPack 保存为 JSON（便于离线调试与回放）。"""
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "ComponentPack":
        """从 JSON 加载 ComponentPack。"""
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise TypeError("component pack json must be an object")
        return ComponentPack.from_dict(obj)
