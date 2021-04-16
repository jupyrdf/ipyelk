# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
# from typing import Dict, List, Optional

from ipywidgets import DOMWidget
from pydantic import BaseModel, Field

# from ipyelk.diagram.elk_model import strip_none
from .elements import ElementShape, add_excluded_fields


class Path(ElementShape):
    use: str = Field(..., description="SVG path string")
    type: str = "node:path"

    @classmethod
    def from_list(cls, segments, closed=False):
        d = "M" + "L".join([f"{x},{y}" for x, y in segments])
        if closed:
            d += "Z"
        return Path(use=d)


class Circle(ElementShape):
    radius: float = 0
    type: str = "node:round"

    def dict(self, **kwargs):
        self.width = self.radius * 2
        self.height = self.radius * 2
        kwargs = add_excluded_fields(kwargs, excluded=["radius"])
        data = super().dict(**kwargs)

        data["x"] = self.radius if self.x is None else self.x
        data["y"] = self.radius if self.y is None else self.y
        return data


class SVG(ElementShape):
    use: str = ""
    type: str = "node:svg"

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props


class Ellipse(ElementShape):
    rx: float = 0
    ry: float = 0

    type: str = "node:round"

    class Config:
        excluded = ["metadata"]

    def dict(self, **kwargs):
        if self.rx and not self.width:
            self.width = self.rx * 2
        if self.ry and not self.height:
            self.height = self.ry * 2
        kwargs = add_excluded_fields(kwargs, excluded=["rx", "ry"])
        data = super().dict(**kwargs)

        return data


class Diamond(ElementShape):
    type: str = "node:diamond"


class Comment(ElementShape):
    type: str = "node:comment"
    use: str = Field(str(15), description="The size of the cornor notch as a string")

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["use"] = str(data["use"])
        return data


class Rect(ElementShape):
    type: str = "node"


class Use(ElementShape):
    type: str = "node:use"
    use: str = Field(..., description="Identifier to use for a reference")

    def get_shape_props(self):
        props = super().get_shape_props()
        props.update({"use": str(self.value)})
        return props


class Point(BaseModel):
    x: float = 0
    y: float = 0

    def __init__(self, x=0, y=0):
        super().__init__(x=x, y=y)


class Image(ElementShape):
    type: str = "node:image"
    use: str = Field(..., description="Image URL")


class ForeignObject(ElementShape):
    type: str = "node:foreignobject"
    use: str = Field(..., description="Foreign object html")


class Widget(ElementShape):
    type: str = "node:widget"
    widget: DOMWidget = None

    class Config:
        arbitrary_types_allowed = True

    def dict(self, **kwargs):
        kwargs = add_excluded_fields(kwargs, excluded=["widget"])
        data = super().dict(**kwargs)
        data["use"] = self.widget.model_id
        return data


class HTML(ElementShape):
    type: str = "node:html"
    use: str = Field(..., description="HTML code")


class Icon(ElementShape):
    type: str = "label:icon"
    use: str = " "

    def __call__(self):
        # TODO make label?
        pass

    def to_json(self, id=None):
        """Returns a valid elk node dictionary"""
        data = super().to_json(id=id)
        data["text"] = " "  # can't be none or completely empty string
        return data

    def get_shape_props(self):
        props = super().get_shape_props()
        if self.value:
            props.update({"use": str(self.value)})
        return props
