from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TITLE = "Default Title"


@dataclass(slots=True)
class Location:
    """Location information of a component on a PDF page.

    Attributes:
        bbox: Bounding box coordinates [x0, y0, x1, y1].
        page: Page number, starting from 1.
        file_name: File name, used for multi-document Q&A.
    """

    bbox: list[float]
    page: int
    file_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes the location information to a dictionary."""
        d = {"bbox": list(self.bbox), "page": int(self.page)}
        if self.file_name:
            d["file_name"] = self.file_name
        return d

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "Location":
        """Deserializes from a dictionary to a Location object."""
        bbox = obj.get("bbox")
        page = obj.get("page")
        file_name = obj.get("file_name")
        if not isinstance(bbox, list) or len(bbox) != 4:
            bbox = [0.0, 0.0, 0.0, 0.0]
        bbox_f = [float(x) for x in bbox[:4]]
        return Location(bbox=bbox_f, page=int(page or 0), file_name=file_name)


@dataclass(slots=True)
class Component:
    """Basic document component.

    Represents the smallest semantic unit extracted from a PDF (e.g., a paragraph of text, an image, a table, etc.).

    Attributes:
        type: Component type (e.g., 'text', 'image', 'chart', 'table', 'header', 'footer', etc.).
        title: Component title, defaults to "Default Title".
        title_level: Title level used to build hierarchical structures (1 is the highest level).
        metadata: Stores additional metadata related to this component.
        data: Original content or extracted text content of the component.
        location: List of positions for this component in the PDF pages (may span multiple areas or pages).
    """

    type: str
    title: str = TITLE
    title_level: int = 1
    metadata: Any | None = None
    data: str = ""
    location: list[Location] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the component to a dictionary."""
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
        """Deserializes from a dictionary to a Component object."""
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
    """A collection of supplementary document information.

    Aggregates auxiliary information such as headers, footers, page numbers, and sidebars by page number.

    Attributes:
        header: Mapping from page number to header components.
        footer: Mapping from page number to footer components.
        number: Mapping from page number to page number components.
        aside: Mapping from page number to sidebar components.
    """

    header: dict[int, Component] = field(default_factory=dict)
    footer: dict[int, Component] = field(default_factory=dict)
    number: dict[int, Component] = field(default_factory=dict)
    aside: dict[int, Component] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the supplementary information to a dictionary."""

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
        """Deserializes from a dictionary to a Supplement object."""

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
    """A collection of components for the entire document.

    Contains a list of body components and supplementary information.

    Attributes:
        body: List of all components in the document body.
        supplement: Supplementary information such as headers and footers.
    """

    body: list[Component] = field(default_factory=list)
    supplement: Supplement = field(default_factory=Supplement)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the packed object to a dictionary."""
        return {
            "body": [co.to_dict() for co in self.body],
            "supplement": self.supplement.to_dict(),
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> "ComponentPack":
        """Deserializes from a dictionary to a ComponentPack object."""
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

    def dump_json(self, path: str | Path) -> None:
        """Saves the ComponentPack as a JSON file.

        Used for offline debugging, playback, or intermediate result persistence.

        Args:
            path: The path to save the JSON file to.
        """
        p = Path(path)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def load_json(path: str) -> "ComponentPack":
        """Load a ComponentPack object from a JSON file."""
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise TypeError("component pack json must be an object")
        return ComponentPack.from_dict(obj)
