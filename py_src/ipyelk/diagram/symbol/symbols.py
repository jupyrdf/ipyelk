# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from abc import ABC
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Type

from ipywidgets import DOMWidget

from ipyelk.diagram.elk_model import strip_none


@dataclass
class Symbol(ABC):
    identifier: ClassVar[str] = None
    type: ClassVar[str] = None

    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    children: List["Symbol"] = field(default_factory=list)

    def __hash__(self):
        """Simple hashing function to make it easier to use as a networkx node"""
        return hash(self.id)

    def to_json(self, id=None):
        """Returns a valid elk node dictionary"""
        data = {
            "id": id,
            "children": self.get_children(id=id) or None,
            "properties": self.get_properties(),
            "labels": self.get_labels(id=id),
            "layoutOptions": self.get_layoutOptions(),
            "ports": self.get_ports(id=id) or None,
            **self.bounds(),
        }
        return strip_none(data)

    def position(self):
        pos = {}
        if self.x is not None:
            pos["x"] = self.x
        if self.y is not None:
            pos["y"] = self.y
        return pos

    def bounds(self) -> Dict:
        return {
            "width": self.width or 0,
            "height": self.height or 0,
        }

    def get_labels(self, id=None) -> List:
        return []

    def get_layoutOptions(self) -> Dict:
        return {}

    def get_ports(self, id=None) -> List:
        return []

    def get_children(self, id=None) -> List:
        return [c.to_json() for c in getattr(self, "children", [])]

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
        return self.position()

    @classmethod
    def make_defs(cls, classes: List[Type["Symbol"]] = None) -> Dict:
        """Take a list of classes and return the def dictionary

        :param classes: Subclasses of Symbol. If `None` use the subclasses of
        the current class.
        :type classes: List[Type["Symbol"]]
        :return: Def Dictionary
        :rtype: Dict
        """
        if classes is None:
            classes = cls.__subclasses__()
        return {c.identifier: c.shape for c in classes}


@dataclass
class Path(Symbol):
    value: str = ""
    type = "node:path"

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props

    @classmethod
    def from_list(cls, segments, closed=False):
        d = "M" + "L".join([f"{x},{y}" for x, y in segments])
        if closed:
            d += "Z"
        return Path(value=d)


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
class SVG(Symbol):
    value: str = ""
    type = "node:svg"

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props


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


@dataclass
class Diamond(Symbol):
    type = "node:diamond"


@dataclass
class Comment(Symbol):
    type = "node:comment"
    size: float = 15

    def get_shape_props(self):
        props = super().get_shape_props()
        props.update({"use": str(self.size)})  # size of comment notch
        return props


@dataclass
class Rect(Symbol):
    type = "node"


@dataclass
class Use(Symbol):
    type = "node:use"
    value: str = ""

    def get_shape_props(self):
        props = super().get_shape_props()
        props.update({"use": str(self.value)})
        return props


@dataclass
class Point:
    x: float = 0
    y: float = 0


@dataclass
class Image(Symbol):
    type = "node:image"
    value: str = None

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": self.value})
        return props


@dataclass
class ForeignObject(Symbol):
    type = "node:foreignobject"
    value: str = ""

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props = {"use": str(self.value)}
        return props


@dataclass
class Widget(Symbol):
    type = "node:widget"
    widget: Type[DOMWidget] = None

    def get_shape_props(self):
        props = super().get_shape_props()
        if isinstance(self.widget, DOMWidget):
            props.update({"use": self.widget.model_id})
        return props


@dataclass
class HTML(Symbol):
    type = "node:html"
    value: str = ""

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props


@dataclass
class Icon(Symbol):
    type = "label:icon"
    value: str = " "

    def to_json(self, id=None):
        """Returns a valid elk node dictionary"""
        data = super().to_json(id=id)
        data["text"] = " "  # can't be none or completely empty string
        return strip_none(data)

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props
