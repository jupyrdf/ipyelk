# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Shapes select how the frontend draws a node, port, label or edge.

The frontend is the ipyelk JupyterLab extension that draws the diagram in the
browser. A shape is the object in ``properties.shape`` of an element. Its ``type``
string selects the renderer, that is, the frontend view that draws the element.
The other fields hold the data that the renderer draws.
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
    """A point with an ``x`` and a ``y`` coordinate, in pixels.

    :py:class:`~ipyelk.elements.EndpointSymbol` uses points for its ``path_offset``
    and its ``symbol_offset``. The constructor also accepts the two coordinates as
    positional arguments:

    .. code-block:: python

        Point(-1, 0)
    """

    x: float = 0
    y: float = 0

    def __init__(self, x=0, y=0):
        super().__init__(x=x, y=y)


class BaseShape(BaseModel):
    """The base class of all shapes.

    ``type`` is the type string. The frontend uses it to select the renderer. If
    ``type`` is ``None``, the frontend uses the default renderer for the element:
    ``node``, ``port``, ``label`` or ``edge``.
    """

    type: str | None = None

    def dimension(self, key: str) -> float | None:
        """Return the value of ``x``, ``y``, ``width`` or ``height`` to serialize.

        ``key`` is the name of the field. Subclasses override this method to
        calculate a value from other fields. For example, :py:class:`Circle`
        calculates ``width`` from ``radius``.
        """
        return getattr(self, key, None)


class EdgeShape(BaseShape):
    """The shape of an edge: a line along the route of the edge.

    ``start`` and ``end`` are optional symbol identifiers. A symbol identifier is
    the ``identifier`` of a :py:class:`~ipyelk.elements.Symbol` in the ``symbols``
    of the diagram. The renderer draws the ``start`` symbol at the first point of
    the route and the ``end`` symbol at the last point. It turns each symbol to
    the direction of the route at that point.

    If the symbol is an :py:class:`~ipyelk.elements.EndpointSymbol`, its
    ``path_offset`` makes the line shorter and its ``symbol_offset`` moves the
    symbol. An edge shape has no ``use`` field.

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

    All the fields are optional:

    - ``x`` and ``y`` are a position in pixels from the top-left corner of the
      element. Only the renderers of :py:class:`Circle`, :py:class:`Ellipse` and
      :py:class:`SVG` use them.
    - ``width`` and ``height`` are a size in pixels. If the element has no
      ``width`` or ``height`` of its own, the element serializes the value of its
      shape.
    - ``use`` is a string. Each subclass gives ``use`` its own meaning.
    - ``delay`` is a time in milliseconds. Only :py:class:`Widget` uses it.

    The layout can change the size of the element. The renderers draw the size
    that the layout gives. If ``type`` is not the type string of this class or
    of a direct subclass, pydantic raises a ``ValidationError``.
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

    If ``use`` is a symbol identifier, the renderer draws that symbol at the
    ``width`` and ``height`` of the port. If ``use`` is ``None``, the renderer
    draws a rectangle.
    """

    type: str | None = "port"
    use: str | None = Field(None, description="Symbol identifier")


class LabelShape(ElementShape):
    """The shape of a label.

    If ``use`` is a symbol identifier, the renderer draws that symbol in place of
    the text of the label. If ``use`` is ``None``, the renderer draws the text.
    """

    type: str | None = "label"
    use: str | None = Field(None, description="Symbol identifier")


class Icon(LabelShape):
    """A label shape for a symbol in front of the text of a label.

    ``Icon`` is a :py:class:`LabelShape` that requires ``use``. Put a label with
    an ``Icon`` shape in the ``labels`` of another label, the parent label. The
    parent label draws the symbol of its first nested label to the left of its own
    text. A label that is not nested draws the symbol in place of its text.

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
    """The base class of the node shapes.

    Each subclass sets ``type`` to select a renderer and gives ``use`` its own
    meaning. A ``NodeShape`` with no ``type`` draws as a rectangle, the same as
    :py:class:`Rect`.
    """


class Path(NodeShape):
    """An SVG path. ``use`` is the path data, that is, the ``d`` attribute of an
    SVG ``path`` element.

    The path coordinates are pixels from the top-left corner of the node. The
    renderer does not scale the path to the ``width`` and ``height`` of the node.

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
    """A circle with the radius ``radius``, in pixels. It has no ``use``.

    ``Circle`` always calculates ``width`` and ``height`` as two times ``radius``.
    Its ``width`` and ``height`` fields have no effect. ``x`` and ``y`` are the
    center of the circle. If ``x`` or ``y`` is ``None``, its value is ``radius``.

    ``Circle`` and :py:class:`Ellipse` share the ``node:round`` renderer. The
    renderer draws an ellipse that fills the node. If the node has its own
    ``width`` or ``height``, the result is not a circle.

    .. code-block:: python

        NodeProperties(shape=Circle(radius=6))
    """

    type: str = "node:round"
    radius: float = Field(0, exclude=True, description="Radius in pixels")

    def dimension(self, key: str) -> float | None:
        if key in {"width", "height"}:
            return self.radius * 2
        value = super().dimension(key)
        return self.radius if value is None else value


class SVG(NodeShape):
    """SVG markup. ``use`` is the markup as a string.

    The renderer puts the markup in an SVG ``g`` element and moves it by ``x``
    and ``y``, in pixels. The renderer does not scale the markup to the ``width``
    and ``height`` of the node.

    .. warning::

        The frontend inserts ``use`` into the page without changes. Put only
        markup from a source that you trust in ``use``.

    .. code-block:: python

        SVG(use='<circle cx="10" cy="10" r="10"/>', width=20, height=20)
    """

    type: str = "node:svg"
    use: str = Field(..., description="SVG markup")


class Ellipse(NodeShape):
    """An ellipse with the radii ``rx`` and ``ry``, in pixels. It has no ``use``.

    ``rx`` is the horizontal radius and ``ry`` is the vertical radius. If
    ``width`` is not set, ``Ellipse`` calculates it as two times ``rx``. If
    ``height`` is not set, ``Ellipse`` calculates it as two times ``ry``.

    The renderer draws the ellipse to fill the node. ``x`` and ``y`` are the
    center of the ellipse. If they are ``None``, the center is the center of the
    node.
    """

    type: str = "node:round"
    rx: float = Field(0, exclude=True, description="Horizontal radius in pixels")
    ry: float = Field(0, exclude=True, description="Vertical radius in pixels")

    def dimension(self, key: str) -> float | None:
        value = super().dimension(key)
        radius = {"width": self.rx, "height": self.ry}.get(key)
        return radius * 2 if radius and not value else value


class Diamond(NodeShape):
    """A diamond, that is, a polygon with four corners. It has no ``use``.

    The four corners are at the middle of the four sides of the node.
    """

    type: str = "node:diamond"


class Comment(NodeShape):
    """A rectangle with a corner notch at the top right.

    The corner notch is the triangle that the renderer removes from the top-right
    corner. ``use`` is the length of the two short sides of the notch in pixels,
    as a string. The default is ``"15"``. ``Comment`` changes a number to a
    string, also when you assign it after construction.

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
    """A rectangle at the ``width`` and ``height`` of the node. It has no ``use``.

    The frontend also draws a rectangle for a node that has no shape.
    """

    type: str = "node"


class Use(NodeShape):
    """A symbol. ``use`` is a symbol identifier.

    A symbol identifier is the ``identifier`` of a
    :py:class:`~ipyelk.elements.Symbol` in the ``symbols`` of the diagram. The
    renderer draws the symbol at the ``width`` and ``height`` of the node.

    .. code-block:: python

        Node(
            properties=NodeProperties(shape=Use(use="final_state")),
            width=12,
            height=12,
        )
    """

    type: str = "node:use"
    use: str = Field(..., description="Symbol identifier")


class Image(NodeShape):
    """An image. ``use`` is the URL of the image.

    The renderer draws the image in an SVG ``image`` element at the ``width``
    and ``height`` of the node.
    """

    type: str = "node:image"
    use: str = Field(..., description="Image URL")


class ForeignObject(NodeShape):
    """HTML in the diagram SVG. ``use`` is HTML markup as a string.

    The renderer puts the markup in a ``div`` in an SVG ``foreignObject``
    element, at the ``width`` and ``height`` of the node. :py:class:`HTML` draws
    HTML markup above the diagram SVG.

    .. warning::

        The frontend inserts ``use`` into the page without changes. Put only
        markup from a source that you trust in ``use``.
    """

    type: str = "node:foreignobject"
    use: str = Field(..., description="HTML markup")


class Widget(NodeShape):
    """A Jupyter widget. ``widget`` is the ipywidgets ``DOMWidget`` to draw.

    The frontend draws a view of ``widget`` in the HTML layer, at the position,
    ``width`` and ``height`` of the node. :py:class:`HTML` describes the HTML
    layer. Serialization writes the ``model_id`` of ``widget`` to ``use``. A
    value that you set in ``use`` has no effect.

    ``delay`` is a time in milliseconds. If ``delay`` is set, the frontend first
    draws the widget without the diagram zoom. After ``delay`` milliseconds, it
    applies the diagram zoom. The ``15_Nesting_Plots`` example sets ``delay`` for
    its plot widgets.

    .. code-block:: python

        Node(
            properties=NodeProperties(shape=Widget(widget=IntSlider())),
            width=320,
            height=40,
        )
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
    """HTML above the diagram SVG. ``use`` is HTML markup as a string.

    The frontend draws the markup in the HTML layer. The HTML layer is a ``div``
    above the diagram SVG that moves and zooms with the diagram. In the HTML
    layer, the markup fills a ``div`` at the position, ``width`` and ``height``
    of the node. The diagram SVG has a rectangle for the node under that ``div``.

    .. warning::

        The frontend inserts ``use`` into the page without changes. Put only
        markup from a source that you trust in ``use``.
    """

    type: str = "node:html"
    use: str = Field(..., description="HTML markup")


Widget.model_rebuild()
