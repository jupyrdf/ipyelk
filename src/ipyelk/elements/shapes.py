# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from ipywidgets import DOMWidget
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
)

from .common import serialize_value


class Point(BaseModel):
    x: float = 0
    y: float = 0

    def __init__(self, x=0, y=0):
        super().__init__(x=x, y=y)


class BaseShape(BaseModel):
    type: str | None = None

    def dimension(self, key: str) -> float | None:
        return getattr(self, key, None)


class EdgeShape(BaseShape):
    type: str | None = "edge"
    start: str | None = None
    end: str | None = None


class ElementShape(BaseShape):
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    use: str | None = Field(None, description="Meaning is specialized in subclasses")
    delay: int | None = Field(
        None,
        description="Only used for delayed rendering of embedded jupyterlab widgets",
    )

    @classmethod
    def valid_subtypes(cls) -> set[str]:
        """Iterate over subclasses and extracts the known `type` defaults"""
        return set(c.model_fields["type"].default for c in cls.__subclasses__()) | {
            cls.model_fields["type"].default,
            None,
        }

    @field_validator("type")
    @classmethod
    def subtype_validator(cls, v):
        """Checks that there is a subclass that defines the `type`"""
        subtypes = cls.valid_subtypes()
        if v not in subtypes:
            raise ValueError(f"Unexpected Subtype: `{v}` not in `{subtypes}`")
        return v

    @model_serializer(mode="wrap")
    def serialize_shape(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = handler(self)
        for key in ("x", "y", "width", "height"):
            value = self.dimension(key)
            if value != getattr(self, key):
                serialize_value(data, key, value, info)
        return data


class PortShape(ElementShape):
    type: str | None = "port"
    use: str | None = Field(None, description="Symbol Identifier")


class LabelShape(ElementShape):
    type: str | None = "label"
    use: str | None = Field(None, description="Symbol Identifier")


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
    radius: float = Field(0, exclude=True)

    def dimension(self, key: str) -> float | None:
        if key in {"width", "height"}:
            return self.radius * 2
        value = super().dimension(key)
        return self.radius if value is None else value


class SVG(NodeShape):
    type: str = "node:svg"
    use: str = Field(..., description="String representing raw svg")


class Ellipse(NodeShape):
    type: str = "node:round"
    rx: float = Field(0, exclude=True)
    ry: float = Field(0, exclude=True)

    def dimension(self, key: str) -> float | None:
        value = super().dimension(key)
        radius = {"width": self.rx, "height": self.ry}.get(key)
        return radius * 2 if radius and not value else value


class Diamond(NodeShape):
    type: str = "node:diamond"


class Comment(NodeShape):
    type: str = "node:comment"
    use: str = Field(str(15), description="The size of the cornor notch as a string")

    # coerce on assignment too (`comment.use = 20`), as the v1 `dict()` override did
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("use", mode="before")
    @classmethod
    def stringify_size(cls, value):
        return str(value) if isinstance(value, (int, float)) else value


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
    widget: DOMWidget = Field(
        exclude=True, description="Ipywidgets as Foreign object html"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_serializer(mode="wrap")
    def serialize_shape(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = super().serialize_shape(handler, info)
        serialize_value(data, "use", self.widget.model_id, info)
        return data


class HTML(NodeShape):
    type: str = "node:html"
    use: str = Field(..., description="HTML code")


Widget.model_rebuild()
