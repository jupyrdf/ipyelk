# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Shape classes. A shape selects how the frontend draws an element.

The *Shapes* page of the API reference describes the shapes and the terms used here.
"""

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
    """A point in pixels. ``Point(-1, 0)`` is the same as ``Point(x=-1, y=0)``.

    Fields:
        - ``x``, ``y`` (``float``, default ``0``)
    """

    x: float = 0
    y: float = 0

    def __init__(self, x=0, y=0):
        super().__init__(x=x, y=y)


class BaseShape(BaseModel):
    """The base class of all shapes.

    Fields:
        - ``type`` (``str`` or ``None``): the type string, which selects the renderer.
          Each subclass sets its own default. ``None`` selects the default renderer.
    """

    type: str | None = None

    def dimension(self, key: str) -> float | None:
        """Return the value of ``x``, ``y``, ``width`` or ``height`` to serialize.

        ``key`` is the name of the field. A subclass can calculate the value from
        other fields, as :py:class:`Circle` does.
        """
        return getattr(self, key, None)


class EdgeShape(BaseShape):
    """The shape of an edge: a line along the route of the edge.

    The renderer draws the ``start`` symbol at the first point of the route and the
    ``end`` symbol at the last point, turned to the direction of the route. If no
    symbol has the identifier, the renderer draws nothing at that end. An
    :py:class:`~ipyelk.elements.EndpointSymbol` can also make the line shorter.

    Fields:
        - ``start``, ``end`` (``str`` or ``None``, default ``None``): a symbol
          identifier.

    .. code-block:: python

        EdgeProperties(shape=EdgeShape(end="arrow"))
    """

    type: str | None = "edge"
    start: str | None = Field(
        None, description="Symbol identifier to draw at the start of the edge"
    )
    end: str | None = Field(
        None, description="Symbol identifier to draw at the end of the edge"
    )


class ElementShape(BaseShape):
    """The base class of the shapes of nodes, ports and labels.

    Fields, all ``None`` by default:
        - ``x``, ``y`` (``float``): a position in pixels in the element. Only
          :py:class:`Circle`, :py:class:`Ellipse` and :py:class:`SVG` use them.
        - ``width``, ``height`` (``float``): a size in pixels. The element serializes
          this size if it has no ``width`` or ``height`` of its own. After a layout,
          the element has the laid-out size as its own size.
        - ``use`` (``str``): each subclass gives ``use`` its own meaning.
        - ``delay`` (``int``): a time in milliseconds. Only :py:class:`Widget` uses it.
    """

    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    use: str | None = Field(None, description="Each subclass gives its own meaning")
    delay: int | None = Field(
        None,
        description="Milliseconds before a Widget node applies the diagram zoom",
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
    """The shape of a port.

    Fields:
        - ``use`` (``str`` or ``None``, default ``None``): a symbol identifier, drawn
          at the size of the port. If ``use`` is ``None`` or no symbol has it, the
          renderer draws a rectangle.
    """

    type: str | None = "port"
    use: str | None = Field(None, description="Symbol identifier")


class LabelShape(ElementShape):
    """The shape of a label.

    If ``width`` and ``height`` are both set and not 0, the frontend does not measure
    the text of the label.

    Fields:
        - ``use`` (``str`` or ``None``, default ``None``): a symbol identifier, drawn in
          place of the text. If ``use`` is ``None`` or no symbol has it, the renderer
          draws the text.
    """

    type: str | None = "label"
    use: str | None = Field(None, description="Symbol identifier")


class Icon(LabelShape):
    """A label shape for a symbol in front of the text of its parent label.

    Put a label with an ``Icon`` shape first in the ``labels`` of another label, the
    parent label. The parent label draws the symbol to the left of its own text. A
    label that is not nested draws the symbol in place of its text.

    Fields:
        - ``use`` (``str``, required): a symbol identifier.

    .. code-block:: python

        icon = Icon(use="class", width=12, height=12)
        Label(
            text="Point",
            labels=[Label(text=" ", properties=LabelProperties(shape=icon))],
        )
    """

    type: str = "label:icon"
    use: str = Field(..., description="Symbol identifier")


class NodeShape(ElementShape):
    """The base class of the node shapes. With no ``type``, it draws a rectangle.

    After a layout, the node gets back a ``NodeShape``, not the subclass that you set.
    The *Width and height* section of the *Shapes* page explains this.
    """


class Path(NodeShape):
    """An SVG path. The renderer does not scale it to the size of the node.

    Fields:
        - ``use`` (``str``, required): the path data, that is, the ``d`` attribute of
          an SVG ``path`` element. Its coordinates are pixels from the top-left corner
          of the node.

    .. code-block:: python

        Path(use="M 0,0 L 0,100 L 20,30 Z")
        Path.from_list([(0, 0), (0, 100), (20, 30)], closed=True)
    """

    type: str = "node:path"
    use: str = Field(..., description="SVG path data")

    @classmethod
    def from_list(cls, segments, closed=False):
        """Make a ``Path`` of straight lines through the points in ``segments``.

        ``segments`` is a sequence of ``(x, y)`` pairs. If ``closed`` is true, the
        path ends with a line back to the first point.
        """
        d = "M" + "L".join([f"{x},{y}" for x, y in segments])
        if closed:
            d += "Z"
        return Path(use=d)


class Circle(NodeShape):
    """A circle. It serializes ``width`` and ``height`` as two times ``radius``.

    The ``node:round`` renderer does not read ``radius``. It draws an ellipse with half
    the laid-out width and height of the node as its radii. If the laid-out width and
    height differ, the ellipse is not a circle.

    Fields:
        - ``radius`` (``float``, default ``0``): the radius in pixels, not serialized.
          The default gives a node of 0 by 0 pixels.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): the center. If they
          are ``None``, the renderer centers the ellipse in the node.
        - ``width``, ``height``: these fields have no effect.

    .. code-block:: python

        NodeProperties(shape=Circle(radius=6))
    """

    type: str = "node:round"
    radius: float = Field(0, exclude=True, description="Radius in pixels")

    def dimension(self, key: str) -> float | None:
        if key in {"width", "height"}:
            return self.radius * 2
        # x and y stay unset, so `node:round` centers the ellipse in the laid-out node
        return super().dimension(key)


class SVG(NodeShape):
    """SVG markup. The renderer does not scale it to the size of the node.

    Put only trusted markup in ``use``, as the warning on the *Shapes* page explains.

    Fields:
        - ``use`` (``str``, required): the SVG markup.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): the offset of the
          markup in pixels. ``None`` is 0.

    .. code-block:: python

        SVG(use='<circle cx="10" cy="10" r="10"/>', width=20, height=20)
    """

    type: str = "node:svg"
    use: str = Field(..., description="SVG markup")


class Ellipse(NodeShape):
    """An ellipse. The ``node:round`` renderer draws it as it draws :py:class:`Circle`.

    Fields:
        - ``rx``, ``ry`` (``float``, default ``0``): the horizontal and the vertical
          radius in pixels, not serialized.
        - ``width``, ``height`` (``float`` or ``None``, default ``None``): if ``width``
          is ``None`` or 0, ``Ellipse`` serializes two times ``rx``. The same rule
          applies to ``height`` and ``ry``.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): as for ``Circle``.
    """

    type: str = "node:round"
    rx: float = Field(0, exclude=True, description="Horizontal radius in pixels")
    ry: float = Field(0, exclude=True, description="Vertical radius in pixels")

    def dimension(self, key: str) -> float | None:
        value = super().dimension(key)
        radius = {"width": self.rx, "height": self.ry}.get(key)
        return radius * 2 if radius and not value else value


class Diamond(NodeShape):
    """A polygon with its four corners at the middle of the four sides of the node."""

    type: str = "node:diamond"


class Comment(NodeShape):
    """A rectangle with a corner notch, a triangle cut from the top-right corner.

    Fields:
        - ``use`` (``str``, default ``"15"``): the length in pixels of the two short
          sides of the notch. ``Comment`` changes a number to a string, also on
          assignment. For ``"0"`` or a string that is not a number, the renderer
          draws a 15 pixel notch.

    .. code-block:: python

        Comment(use=20).use == "20"
    """

    type: str = "node:comment"
    use: str = Field(str(15), description="Size of the corner notch, as a string")

    # coerce on assignment too (`comment.use = 20`), as the v1 `dict()` override did
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("use", mode="before")
    @classmethod
    def stringify_size(cls, value):
        return str(value) if isinstance(value, (int, float)) else value


class Rect(NodeShape):
    """A rectangle at the size of the node. A node with no shape draws the same."""

    type: str = "node"


class Use(NodeShape):
    """A symbol at the size of the node.

    Fields:
        - ``use`` (``str``, required): a symbol identifier. If no symbol has it, the
          renderer draws nothing.

    .. code-block:: python

        NodeProperties(shape=Use(use="final_state"))
    """

    type: str = "node:use"
    use: str = Field(..., description="Symbol identifier")


class Image(NodeShape):
    """An image in an SVG ``image`` element, at the size of the node.

    Fields:
        - ``use`` (``str``, required): the URL of the image.
    """

    type: str = "node:image"
    use: str = Field(..., description="Image URL")


class ForeignObject(NodeShape):
    """HTML markup in an SVG ``foreignObject`` element in the diagram SVG.

    Put only trusted markup in ``use``, as the warning on the *Shapes* page explains.

    Fields:
        - ``use`` (``str``, required): the HTML markup.
    """

    type: str = "node:foreignobject"
    use: str = Field(..., description="HTML markup")


class Widget(NodeShape):
    """A Jupyter widget in the HTML layer, which :py:class:`HTML` describes.

    Fields:
        - ``widget`` (ipywidgets ``DOMWidget``, required): the widget to draw.
          Serialization writes its ``model_id`` to ``use``, so a value in ``use`` has
          no effect.
        - ``delay`` (``int`` or ``None``, default ``None``): a time in milliseconds.
          If it is set, the frontend applies the diagram zoom to the widget only
          after ``delay``. The ``15_Nesting_Plots`` example uses it.

    .. code-block:: python

        NodeProperties(shape=Widget(widget=IntSlider()))
    """

    type: str = "node:widget"
    widget: DOMWidget = Field(
        exclude=True, description="The ipywidgets DOMWidget to draw in the node"
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
    """HTML markup in the HTML layer, at the position and size of the node.

    The HTML layer is a ``div`` above the diagram SVG that moves and zooms with the
    diagram. Put only trusted markup in ``use``, as the warning on the *Shapes* page
    explains.

    Fields:
        - ``use`` (``str``, required): the HTML markup.
    """

    type: str = "node:html"
    use: str = Field(..., description="HTML markup")


Widget.model_rebuild()
