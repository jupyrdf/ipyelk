# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
# from typing import Dict, List, Optional

from typing import Optional, Set

from ipywidgets import DOMWidget
from pydantic import BaseModel, Field, validator

from .common import add_excluded_fields


class Point(BaseModel):
    x: float = 0
    y: float = 0

    class Config:
        copy_on_model_validation = False

    def __init__(self, x=0, y=0):
        super().__init__(x=x, y=y)


class BaseShape(BaseModel):
    type: Optional[str]

    class Config:
        copy_on_model_validation = False


class EdgeShape(BaseShape):
    type: Optional[str] = "edge"
    start: Optional[str]
    end: Optional[str]


class ElementShape(BaseShape):
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]
    use: Optional[str] = Field(None, description="Meaning is specialized in subclasses")

    @classmethod
    def valid_subtypes(cls) -> Set[str]:
        """Iterate over subclasses and extracts the known `type` defaults"""
        return set(c.__fields__["type"].default for c in cls.__subclasses__()) | {
            cls.__fields__["type"].default,
            None,
        }

    @validator("type")
    def subtype_validator(cls, v):
        """Checks that there is a subclass that defines the `type`"""
        subtypes = cls.valid_subtypes()
        if v not in subtypes:
            raise ValueError(f"Unexpected Subtype: `{v}` not in `{subtypes}`")
        return v


class PortShape(ElementShape):
    type: Optional[str] = "port"
    use: Optional[str] = Field(None, description="Symbol Identifier")


class LabelShape(ElementShape):
    type: Optional[str] = "label"
    use: Optional[str] = Field(None, description="Symbol Identifier")


class Icon(LabelShape):
    type: str = "label:icon"
    use: str = Field(..., description="Symbol Identifier")


class NodeShape(ElementShape):
    pass


class Path(NodeShape):
    type: str = "node:path"
    use: str = Field(..., description="SVG path string")

    @classmethod
    def from_list(cls, segments, closed=False):
        d = "M" + "L".join([f"{x},{y}" for x, y in segments])
        if closed:
            d += "Z"
        return Path(use=d)


class Circle(NodeShape):
    type: str = "node:round"
    radius: float = 0

    def dict(self, **kwargs):
        self.width = self.radius * 2
        self.height = self.radius * 2
        kwargs = add_excluded_fields(kwargs, excluded=["radius"])
        data = super().dict(**kwargs)

        data["x"] = self.radius if self.x is None else self.x
        data["y"] = self.radius if self.y is None else self.y
        return data


class SVG(NodeShape):
    type: str = "node:svg"
    use: str = Field(..., description="String representing raw svg")


class Ellipse(NodeShape):
    type: str = "node:round"
    rx: float = 0
    ry: float = 0

    class Config:
        copy_on_model_validation = False
        excluded = ["metadata"]

    def dict(self, **kwargs):
        if self.rx and not self.width:
            self.width = self.rx * 2
        if self.ry and not self.height:
            self.height = self.ry * 2
        kwargs = add_excluded_fields(kwargs, excluded=["rx", "ry"])
        data = super().dict(**kwargs)

        return data


class Diamond(NodeShape):
    type: str = "node:diamond"


class Comment(NodeShape):
    type: str = "node:comment"
    use: str = Field(str(15), description="The size of the cornor notch as a string")

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["use"] = str(data["use"])
        return data


class Rect(NodeShape):
    type: str = "node"


class Use(NodeShape):
    type: str = "node:use"
    use: str = Field(..., description="Symbol identifier to use")


class Image(NodeShape):
    type: str = "node:image"
    use: str = Field(..., description="Image URL")


class ForeignObject(NodeShape):
    type: str = "node:foreignobject"
    use: str = Field(..., description="Foreign object html")


class Widget(NodeShape):
    type: str = "node:widget"
    widget: DOMWidget = Field(description="Ipywidgets as Foreign object html")

    class Config:
        copy_on_model_validation = False
        arbitrary_types_allowed = True

    def dict(self, **kwargs):
        kwargs = add_excluded_fields(kwargs, excluded=["widget"])
        data = super().dict(**kwargs)
        data["use"] = self.widget.model_id
        return data


class HTML(NodeShape):
    type: str = "node:html"
    use: str = Field(..., description="HTML code")
