# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from abc import ABC
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Hashable, List, Optional
from uuid import uuid4


from ipyelk.diagram.elk_model import strip_none


def make_id():
    return str(uuid4())


@dataclass
class Symbol(ABC):
    identifier: ClassVar[str] = None
    type: ClassVar[str] = None
    id: Optional[Hashable] = None

    width: Optional[float] = None
    height: Optional[float] = None
    children: List["Symbol"] = field(default_factory=list)
    x: Optional[float] = None
    y: Optional[float] = None

    def __hash__(self):
        """Simple hashing function to make it easier to use as a networkx node"""
        return hash(self.id)

    def to_json(self):
        """Returns a valid elk node dictionary"""
        data = {
            "id": self.id,  # maybe need flag to strip id
            "children": [c.to_json() for c in getattr(self, "children", [])],
            "properties": self.get_properties(),
            "labels": self.get_labels(),
            "layoutOptions": self.get_layoutOptions(),
            "ports": self.get_ports(),
            **self.bounds(),
            **self.position(),
        }
        return strip_none(data)

    def position(self):
        return {
            "x": self.x or 0,
            "y": self.y or 0,
        }

    def bounds(self) -> Dict:
        return {
            "width": self.width or 0,
            "height": self.height or 0,
        }

    def get_labels(self) -> List:
        return []

    def get_layoutOptions(self) -> Dict:
        return {}

    def get_ports(self) -> List:
        return []

    def get_properties(self) -> Dict:
        properties = {}
        typed = self.type
        if typed:
            properties["type"] = typed
        shape_data = self.get_shape_props()
        if shape_data:
            properties["shape"] = shape_data
        # TODO css classes?
        return properties

    def get_shape_props(self) -> Optional[Dict]:
        return None


@dataclass
class Path(Symbol):
    shape: str = ""
    type = "node:path"

    def get_shape_props(self):
        return {"use": self.shape}

    @classmethod
    def from_list(cls, segments, closed=False):
        d = "M" + "L".join([f"{x},{y}" for x, y in segments])
        if closed:
            d += "Z"
        return Path(shape=d)


@dataclass
class Circle(Symbol):
    radius: float = 0

    type = "node:round"

    def bounds(self) -> Dict:
        return {
            "width": self.radius * 2,
            "height": self.radius * 2,
        }

    def position(self):
        return {
            "x": self.radius if self.x is None else self.x,
            "y": self.radius if self.y is None else self.y,
        }


@dataclass
class RawSVG(Symbol):
    value: str = ""

    type = "node:raw"

    def get_shape_props(self):
        return {
            "use": self.value,
        }


@dataclass
class Ellipse(Symbol):
    rx: float = 0
    ry: float = 0

    type = "node:round"

    def bounds(self) -> Dict:
        return {
            "width": self.rx * 2,
            "height": self.ry * 2,
        }

    def position(self):
        return {
            "x": self.rx if self.x is None else self.x,
            "y": self.ry if self.y is None else self.y,
        }


@dataclass
class Diamond(Symbol):
    type = "node:diamond"


@dataclass
class Comment(Symbol):
    type = "node:comment"
    size: float = 15

    def get_shape_props(self):
        return {"use": self.size}  # size of comment notch


@dataclass
class Rect(Symbol):
    type = "node"


@dataclass
class Point:
    x: float = 0
    y: float = 0

@dataclass
class Image(Symbol):
    type: "node:image"
    value: str = None

    def get_shape_props(self):
        return {"use": self.value}