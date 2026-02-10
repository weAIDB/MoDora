from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TITLE = "Default Title"


@dataclass(slots=True)
class Location:
    """
    组件在 PDF 页面上的定位信息。

    Attributes:
        bbox: 边界框坐标 [x0, y0, x1, y1]。
        page: 页码，从 1 开始计数。
        file_name: 文件名，用于多文档问答。
    """

    bbox: list[float]
    page: int
    file_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将定位信息序列化为字典。"""
        d = {"bbox": list(self.bbox), "page": int(self.page)}
        if self.file_name:
            d["file_name"] = self.file_name
        return d

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Location":
        """从字典反序列化为 Location 对象。"""
        bbox = obj.get("bbox")
        page = obj.get("page")
        file_name = obj.get("file_name")
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        bbox_f = [float(x) for x in bbox[:4]]
        return Location(bbox=bbox_f, page=int(page or 0), file_name=file_name)


@dataclass(slots=True)
class Component:
    """
    文档基础组件。
    表示从 PDF 中提取出的最小语义单元（如一段文字、一张图片、一个表格等）。

    Attributes:
        type: 组件类型 (如 'text', 'image', 'chart', 'table', 'header', 'footer' 等)。
        title: 组件标题，默认为 "Default Title"。
        title_level: 标题级别，用于构建层级结构 (1 为最高级)。
        metadata: 存储与该组件相关的额外元数据。
        data: 组件的原始内容或提取出的文本内容。
        location: 该组件在 PDF 页面中的位置列表 (可能跨越多个区域或页面)。
    """

    type: str
    title: str = TITLE
    title_level: int = 1
    metadata: Any | None = None
    data: str = ""
    location: list[Location] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """将组件序列化为字典。"""
        return {
            "type": self.type,
            "title": self.title,
            "title_level": self.title_level,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Component":
        """从字典反序列化为 Component 对象。"""
        locs: list[Location] = []
        raw_locs = obj.get("location")
        if isinstance(raw_locs, list):
            for it in raw_locs:
                if isinstance(it, dict):
                    locs.append(Location.from_dict(it))
        return Component(
            type=str(obj.get("type") or ""),
            title=str(obj.get("title") or TITLE),
            title_level=obj.get("title_level" or 1),
            metadata=obj.get("metadata"),
            data=str(obj.get("data") or ""),
            location=locs,
        )


@dataclass(slots=True)
class Supplement:
    """
    文档补充信息集合。
    按页码聚合页眉、页脚、页码和边栏等辅助信息。

    Attributes:
        header: 页码到页眉组件的映射。
        footer: 页码到页脚组件的映射。
        number: 页码到页码组件的映射。
        aside: 页码到边栏组件的映射。
    """

    header: dict[int, Component] = field(default_factory=dict)
    footer: dict[int, Component] = field(default_factory=dict)
    number: dict[int, Component] = field(default_factory=dict)
    aside: dict[int, Component] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """将补充信息序列化为字典。"""

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
        """从字典反序列化为 Supplement 对象。"""

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
    """
    整份文档的组件打包对象。
    包含正文组件列表和补充信息。

    Attributes:
        body: 文档正文中的所有组件列表。
        supplement: 文档的页眉页脚等补充信息。
    """

    body: list[Component] = field(default_factory=list)
    supplement: Supplement = field(default_factory=Supplement)

    def to_dict(self) -> dict[str, Any]:
        """将打包对象序列化为字典。"""
        return {
            "body": [co.to_dict() for co in self.body],
            "supplement": self.supplement.to_dict(),
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "ComponentPack":
        """从字典反序列化为 ComponentPack 对象。"""
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
        """将 ComponentPack 保存为 JSON 文件（用于离线调试、回放或中间结果持久化）。"""
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "ComponentPack":
        """从 JSON 文件加载 ComponentPack 对象。"""
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise TypeError("component pack json must be an object")
        return ComponentPack.from_dict(obj)
