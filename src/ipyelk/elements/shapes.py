# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Shape classes. A shape selects how the frontend draws an element.

The *Shapes* page of the API reference describes the shapes and the terms used here.
"""

from __future__ import annotations

import builtins
import functools
import warnings
from typing import Annotated, ClassVar

from ipywidgets import DOMWidget, widget_serialization
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic_core import PydanticKnownError

from .common import serialize_value


def _not_a_bool(value: object) -> object:
    # pydantic reads True as 1.0 in a float field. pydantic turns a ValueError from a
    # validation function into a ValidationError, but a TypeError escapes it.
    if isinstance(value, bool):
        raise ValueError("Input should be a number of pixels, not a bool")  # ruff: ignore[type-check-without-type-error]
    return value


# the payload types of `use`, one for each meaning. The *Shapes* page lists them.

#: The ``identifier`` of a symbol in the diagram's ``defs``.
SymbolId = Annotated[str, Field(min_length=1)]

#: The ``d`` attribute of an SVG ``path``: a move command and a number first, then path
#: commands, numbers, commas and ASCII whitespace, as the SVG grammar allows.
PathData = Annotated[
    str,
    Field(
        pattern=r"^[ \t\n\r\f]*[Mm][ \t\n\r\f]*[0-9+\-.][ \t\n\r\fMmZzLlHhVvCcSsQqTtAa0-9eE+\-.,]*$"
    ),
]

#: SVG or HTML markup. The frontend inserts it as it is, so it must be trusted.
Markup = str

#: The URL of an image: absolute, relative to the notebook, or a ``data:`` URL.
ImageUrl = Annotated[str, Field(min_length=1)]

# the constraints before the function, so that the JSON schema has `minimum`
#: The size of a comment's notch in pixels: a finite number, 0 or more.
NotchSize = Annotated[
    float, Field(ge=0, allow_inf_nan=False), BeforeValidator(_not_a_bool)
]


class Point(BaseModel):
    """A point in pixels. ``Point(-1, 0)`` is the same as ``Point(x=-1, y=0)``.

    Fields:
        - ``x``, ``y`` (``float``, default ``0``)
    """

    x: float = 0
    y: float = 0

    # BaseModel.__init__ takes keyword arguments only. This one allows Point(x, y). But
    # pydantic also calls it to validate a nested Point from a dict, as a new validation
    # without the lenient extra and context of from_wire(). So Point keeps the default
    # extra="ignore": it is the one model that does not forbid unknown keys.
    def __init__(self, x=0, y=0, **data):
        super().__init__(x=x, y=y, **data)


class BaseShape(BaseModel):
    """The base class of all shapes.

    Fields:
        - ``type`` (``str`` or ``None``): the type string, which selects the renderer.
          Each subclass sets its own default. ``None`` selects the default renderer.

    A subclass whose ``type`` default is a string that differs from the ``type``
    default of its parent adds itself to :py:attr:`json_classes` when Python defines
    it. So JSON loads a shape with that type string as that class. This also applies
    to a subclass outside ipyelk, when its module is imported. A subclass that keeps
    the ``type`` of its parent does not add itself, so the parent class still loads
    that type string. If a second class has a type string that is already in
    ``json_classes``, its definition warns with a ``UserWarning`` and the second class
    replaces the first, unless it sets :py:attr:`loads_from_json` to ``False``. A class
    with the same module and name as the first, for example after a module reload,
    replaces it with no warning.
    """

    type: str | None = None

    # builtins.type: the `type` field hides the builtin in the class body
    #: The class that loads each type string from JSON.
    json_classes: ClassVar[dict[str, builtins.type[BaseShape]]] = {}

    #: ``False`` keeps the class out of ``json_classes``. A subclass does not inherit it.
    loads_from_json: ClassVar[bool] = True

    #: an unknown key is a typo, or a field of another shape class. An assignment
    #: validates as a construction does.
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: object) -> None:
        """Add ``cls`` to ``json_classes`` if it has a type string of its own."""
        super().__pydantic_init_subclass__(**kwargs)
        tag = cls.model_fields["type"].default
        inherited = {
            base.model_fields["type"].default
            for base in cls.__bases__
            if issubclass(base, BaseShape)
        }
        if not isinstance(tag, str) or tag in inherited:
            return
        if not cls.__dict__.get("loads_from_json", True):
            return
        taken = BaseShape.json_classes.get(tag)
        # the same class defined again, for example by a module reload, replaces it
        if taken is not None and (taken.__module__, taken.__qualname__) != (
            cls.__module__,
            cls.__qualname__,
        ):
            msg = (
                f"{cls.__module__}.{cls.__qualname__} replaces"
                f" {taken.__module__}.{taken.__qualname__} as the class that loads the"
                f" shape type {tag!r} from JSON. Give it another type, or set"
                " `loads_from_json = False` on it."
            )
            # a warning, not an error: a notebook can rename a class and run it again
            warnings.warn(msg, UserWarning, stacklevel=3)
        BaseShape.json_classes[tag] = cls

    def dimension(self, key: str) -> float | None:
        """Return the value of ``x``, ``y``, ``width`` or ``height`` to serialize.

        ``key`` is the name of the field. A subclass can calculate the value from
        other fields, as :py:class:`Circle` does.
        """
        return getattr(self, key, None)


def payload_class(cls: type[BaseShape], tag: object) -> type[BaseShape] | None:
    """Return the class whose ``use`` a ``cls`` with the type string ``tag`` takes.

    It is the class of ``tag`` in ``json_classes``, if ``tag`` is not the type string
    of ``cls``. So ``NodeShape(type="node:comment")`` takes the ``use`` of a
    ``Comment``, and its JSON is the JSON of a ``Comment`` (#244). ``None`` means that
    ``cls`` validates ``use`` itself.
    """
    if not isinstance(tag, str) or tag == cls.model_fields["type"].default:
        return None
    found = BaseShape.json_classes.get(tag)
    return found if found is not None and "use" in found.model_fields else None


def payload_type(cls: type[BaseShape]) -> TypeAdapter:
    """Return the type of the ``use`` of ``cls``, with its constraints.

    It has the annotation of the field and its metadata, such as a ``Field``
    constraint or a ``BeforeValidator``, but not a ``field_validator`` of ``cls``.
    """
    # a class with a forward reference changes its fields when it is rebuilt
    if not cls.__pydantic_complete__:
        return new_payload_type(cls)
    return cached_payload_type(cls)


def new_payload_type(cls: type[BaseShape]) -> TypeAdapter:
    field = cls.model_fields["use"]
    if not field.metadata:
        return TypeAdapter(field.annotation)
    return TypeAdapter(Annotated[(field.annotation, *field.metadata)])


cached_payload_type = functools.cache(new_payload_type)


def validate_payload(cls: type[BaseShape], value: object) -> object:
    """Validate ``value`` as the ``use`` of ``cls``.

    ``None`` is no payload, which the JSON leaves out, so it raises only if ``cls``
    requires ``use``.
    """
    if value is None:
        if cls.model_fields["use"].is_required():
            raise PydanticKnownError("missing")
        return None
    return payload_type(cls).validate_python(value)


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
          the element holds the laid-out size, and the shape's size still wins over
          it as the input to the next layout. The *Width and height* section of the
          *Shapes* page explains this.
        - ``use`` (``str``): the payload. Each built-in subclass gives ``use`` its
          own meaning and type. A custom shape type can give it any meaning. With the
          type string of another class, for example ``NodeShape(type="node:path")``,
          ``use`` has the type of that class, here :py:data:`PathData`.
        - ``delay`` (``int``): a time in milliseconds. Only :py:class:`Widget` uses it.
    """

    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    # validate_default: a type string can require use
    use: str | None = Field(
        None, description="The payload of a custom shape type", validate_default=True
    )
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

    @field_validator("use", mode="wrap")
    @classmethod
    def use_of_type(
        cls, value, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ):
        """Validate ``use`` as the class of the type string does."""
        found = payload_class(cls, info.data.get("type"))
        return handler(value) if found is None else validate_payload(found, value)

    @field_serializer("use", mode="wrap")
    def serialize_use(
        self, value, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        """Write ``use`` as the class of the type string does, for example a number."""
        found = payload_class(type(self), self.type)
        if found is None:
            return handler(value)
        payload = payload_type(found)
        if info.mode_is_json():
            return payload.dump_python(value, mode="json")
        return payload.dump_python(value)

    @model_validator(mode="before")
    @classmethod
    def use_of_new_type(cls, data, info: ValidationInfo):
        """Validate ``use`` again when ``type`` is assigned."""
        # an assignment validates only its own field, but the type selects the payload
        if info.field_name == "type" and isinstance(data, dict):
            # on a copy, so its model_post_init and after validators run on the copy too
            shape = cls.model_construct(**data)
            cls.__pydantic_validator__.validate_assignment(shape, "use", shape.use)
            data = {**data, "use": shape.use}
        return data

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
        - ``use`` (:py:data:`SymbolId` or ``None``, default ``None``): a symbol
          identifier, drawn at the size of the port. If ``use`` is ``None`` or no
          symbol has it, the renderer draws a rectangle.
    """

    type: str | None = "port"
    use: SymbolId | None = Field(
        None, description="Symbol identifier", validate_default=True
    )


class LabelShape(ElementShape):
    """The shape of a label.

    If ``width`` and ``height`` are both set and not 0, the frontend does not measure
    the text of the label.

    Fields:
        - ``use`` (:py:data:`SymbolId` or ``None``, default ``None``): a symbol
          identifier, drawn in place of the text. If ``use`` is ``None`` or no symbol
          has it, the renderer draws the text.
    """

    type: str | None = "label"
    use: SymbolId | None = Field(
        None, description="Symbol identifier", validate_default=True
    )


class Icon(LabelShape):
    """A label shape for a symbol in front of the text of its parent label.

    Put a label with an ``Icon`` shape first in the ``labels`` of another label, the
    parent label. The parent label draws the symbol to the left of its own text. A
    label that is not nested draws the symbol in place of its text.

    Fields:
        - ``use`` (:py:data:`SymbolId`, required): a symbol identifier.

    .. code-block:: python

        icon = Icon(use="class", width=12, height=12)
        Label(
            text="Point",
            labels=[Label(text=" ", properties=LabelProperties(shape=icon))],
        )
    """

    type: str = "label:icon"
    use: SymbolId = Field(..., description="Symbol identifier")


class NodeShape(ElementShape):
    """The base class of the node shapes. With no ``type``, it draws a rectangle."""


class Path(NodeShape):
    """An SVG path. The renderer does not scale it to the size of the node.

    Fields:
        - ``use`` (:py:data:`PathData`, required): the path data, that is, the ``d``
          attribute of an SVG ``path`` element. It starts with a move, ``M`` or
          ``m``. Its coordinates are pixels from the top-left corner of the node.

    .. code-block:: python

        Path(use="M 0,0 L 0,100 L 20,30 Z")
        Path.from_list([(0, 0), (0, 100), (20, 30)], closed=True)
    """

    type: str = "node:path"
    use: PathData = Field(..., description="SVG path data")

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
    height differ, the ellipse is not a circle. JSON loads a ``Circle`` as an
    :py:class:`Ellipse` of the same size, because JSON does not hold ``radius``.

    Fields:
        - ``radius`` (``float``, default ``0``): the radius in pixels, not serialized.
          The default gives a node of 0 by 0 pixels.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): the center. If they
          are ``None``, the renderer centers the ellipse in the node.
        - ``width``, ``height``: these fields have no effect.
        - ``use``: no payload, so it must be ``None``.

    .. code-block:: python

        NodeProperties(shape=Circle(radius=6))
    """

    type: str = "node:round"
    # it writes the same `node:round` as Ellipse, so JSON loads it as an Ellipse
    loads_from_json = False
    radius: float = Field(0, exclude=True, description="Radius in pixels")
    #: no payload: a value other than ``None`` raises
    use: None = Field(None, exclude=True, description="No payload")

    def dimension(self, key: str) -> float | None:
        if key in {"width", "height"}:
            return self.radius * 2
        # x and y stay unset, so `node:round` centers the ellipse in the laid-out node
        return super().dimension(key)


class SVG(NodeShape):
    """SVG markup. The renderer does not scale it to the size of the node.

    Put only trusted markup in ``use``, as the warning on the *Shapes* page explains.

    Fields:
        - ``use`` (:py:data:`Markup`, required): the SVG markup.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): the offset of the
          markup in pixels. ``None`` is 0.

    .. code-block:: python

        SVG(use='<circle cx="10" cy="10" r="10"/>', width=20, height=20)
    """

    type: str = "node:svg"
    use: Markup = Field(..., description="SVG markup")


class Ellipse(NodeShape):
    """An ellipse. The ``node:round`` renderer draws it as it draws :py:class:`Circle`.

    Fields:
        - ``rx``, ``ry`` (``float``, default ``0``): the horizontal and the vertical
          radius in pixels, not serialized.
        - ``width``, ``height`` (``float`` or ``None``, default ``None``): if ``width``
          is ``None`` or 0, ``Ellipse`` serializes two times ``rx``. The same rule
          applies to ``height`` and ``ry``.
        - ``x``, ``y`` (``float`` or ``None``, default ``None``): as for ``Circle``.
        - ``use``: no payload, so it must be ``None``.
    """

    type: str = "node:round"
    rx: float = Field(0, exclude=True, description="Horizontal radius in pixels")
    ry: float = Field(0, exclude=True, description="Vertical radius in pixels")
    #: no payload: a value other than ``None`` raises
    use: None = Field(None, exclude=True, description="No payload")

    def dimension(self, key: str) -> float | None:
        value = super().dimension(key)
        radius = {"width": self.rx, "height": self.ry}.get(key)
        return radius * 2 if radius and not value else value


class Diamond(NodeShape):
    """A polygon with its four corners at the middle of the four sides of the node.

    It has no payload: ``use`` must be ``None``.
    """

    type: str = "node:diamond"
    #: no payload: a value other than ``None`` raises
    use: None = Field(None, exclude=True, description="No payload")


class Comment(NodeShape):
    """A rectangle with a corner notch, a triangle cut from the top-right corner.

    Fields:
        - ``use`` (:py:data:`NotchSize`, default ``15``): the length in pixels of the
          two short sides of the notch, a finite number of 0 or more. 0 draws no
          notch. The renderer limits the notch to the width and the height of the
          node. A string of a number, as 2.x wrote it, loads as the number.

    .. code-block:: python

        Comment(use=20).use == 20.0
    """

    type: str = "node:comment"
    # the notch is the one payload that is not a string, so it replaces the base type
    use: NotchSize = Field(15, description="Size of the corner notch in pixels")  # type: ignore[assignment]


class Rect(NodeShape):
    """A rectangle at the size of the node. A node with no shape draws the same.

    It has no payload: ``use`` must be ``None``.
    """

    type: str = "node"
    #: no payload: a value other than ``None`` raises
    use: None = Field(None, exclude=True, description="No payload")


class Use(NodeShape):
    """A symbol at the size of the node.

    Fields:
        - ``use`` (:py:data:`SymbolId`, required): a symbol identifier. If no symbol
          has it, the renderer draws nothing.

    .. code-block:: python

        NodeProperties(shape=Use(use="final_state"))
    """

    type: str = "node:use"
    use: SymbolId = Field(..., description="Symbol identifier")


class Image(NodeShape):
    """An image in an SVG ``image`` element, at the size of the node.

    Fields:
        - ``use`` (:py:data:`ImageUrl`, required): the URL of the image.
    """

    type: str = "node:image"
    use: ImageUrl = Field(..., description="Image URL")


class ForeignObject(NodeShape):
    """HTML markup in an SVG ``foreignObject`` element in the diagram SVG.

    Put only trusted markup in ``use``, as the warning on the *Shapes* page explains.

    Fields:
        - ``use`` (:py:data:`Markup`, required): the HTML markup.
    """

    type: str = "node:foreignobject"
    use: Markup = Field(..., description="HTML markup")


def open_widget(model_id: object) -> DOMWidget | None:
    """Return the open widget that has ``model_id``, or ``None``."""
    found = widget_serialization["from_json"](f"IPY_MODEL_{model_id}", None)
    return found if isinstance(found, DOMWidget) else None


class Widget(NodeShape):
    """A Jupyter widget in the HTML layer, which :py:class:`HTML` describes.

    Fields:
        - ``widget`` (ipywidgets ``DOMWidget``, required): the widget to draw.
          Serialization writes its ``model_id`` to ``use``. A ``use`` that is not
          the ``model_id`` of an open ``widget`` raises ``ValidationError``, at
          construction and when you assign ``use``. JSON loads the
          widget that has the ``model_id`` in ``use``. If no open widget has it, ELK
          JSON loads a :py:class:`NodeShape` with the same fields, and a dictionary
          in user code raises.
        - ``delay`` (``int`` or ``None``, default ``None``): a time in milliseconds.
          If it is set and not 0, the frontend applies the diagram zoom to the widget
          only after ``delay``. ``None`` and 0 apply the zoom at once. The ``15_Nesting_Plots`` example uses it.

    .. code-block:: python

        NodeProperties(shape=Widget(widget=IntSlider()))
    """

    type: str = "node:widget"
    widget: DOMWidget = Field(
        exclude=True, description="The ipywidgets DOMWidget to draw in the node"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def find_widget(cls, data, info: ValidationInfo):
        """Load JSON, which has the ``model_id`` of the widget in ``use``."""
        if not isinstance(data, dict):
            return data
        widget, use = data.get("widget"), data.get("use")
        # an assignment passes every field: check use only when it is the new value
        given = info.field_name in {None, "use"}
        if widget is None and use:
            found = open_widget(use)
            if found is not None:
                data = {**data, "widget": found}
        elif (
            given
            and isinstance(widget, DOMWidget)
            # a closed widget has no model_id to check against (#241)
            and getattr(widget, "comm", None) is not None
            and use is not None
        ):
            if use != widget.model_id:
                msg = (
                    f"use {use!r} is not the model_id {widget.model_id!r} of widget."
                    " Serialization writes the model_id to use: leave use out."
                )
                raise ValueError(msg)
        return data

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
        - ``use`` (:py:data:`Markup`, required): the HTML markup.
    """

    type: str = "node:html"
    use: Markup = Field(..., description="HTML markup")


Widget.model_rebuild()


def shape_class(
    family: type[BaseShape], data: object, *, wire: bool = False
) -> type[BaseShape]:
    """Return the class that loads the JSON ``data`` of a shape of ``family``.

    It is the class of the ``type`` in ``data``, if that class is ``family`` or a
    subclass of it, else ``family``. In ELK JSON (``wire``, as ``from_wire`` loads it),
    a :py:class:`Widget` with no open widget for its ``model_id`` loads as a
    :py:class:`NodeShape`, with a warning. Elsewhere, such a ``Widget`` raises, because
    it has no ``widget``.
    """
    if not isinstance(data, dict):
        return family
    tag = data.get("type")
    cls = BaseShape.json_classes.get(tag) if isinstance(tag, str) else None
    if cls is None or not issubclass(cls, family):
        return family
    if wire and issubclass(cls, Widget) and "widget" not in data:
        model_id = data.get("use")
        if open_widget(model_id) is None:
            # a closed widget, or JSON from another kernel: keep the layout result
            msg = (
                f"No open widget has the model_id {model_id!r} of a {tag!r} shape. The"
                " shape loads as a NodeShape with the same JSON."
            )
            warnings.warn(msg, UserWarning, stacklevel=2)
            return NodeShape
    return cls
