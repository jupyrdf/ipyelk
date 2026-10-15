# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import abc
import copy
import textwrap
import weakref
from collections.abc import Mapping
from typing import Any, Type, TypeVar, cast, get_args
from weakref import WeakKeyDictionary

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SerializationInfo,
    SerializeAsAny,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    computed_field,
    field_serializer,
    field_validator,
    model_serializer,
)
from typing_extensions import Self

from ..exceptions import NotFoundError, NotUniqueError
from .common import (
    WIRE_CONTEXT,
    CounterContextManager,
    LayoutOptions,
    from_wire,
    serialize_value,
)
from .registry import Registry, new_id
from .shapes import (
    BaseShape,
    EdgeShape,
    LabelShape,
    NodeShape,
    Point,
    PortShape,
    shape_class,
)
from .shapes import Widget as WidgetShape

exclude_hidden = CounterContextManager()
exclude_layout = CounterContextManager()


class ElementMetadata(BaseModel):
    """An empty metadata structure, subclass and add your own attributes using
    pydantic to have validated element metadata. This metadata will not be used
    for layout purposes but potentially useful for maintaining annotations about
    the elements for downstream applications.
    """


class BaseProperties(BaseModel):
    cssClasses: str = Field("", description="whitespace separated list of css classes")
    shape: SerializeAsAny[BaseShape | None] = None
    key: str | None = Field(
        None, description="Used to provide lookup functionality from owner"
    )
    hidden: bool | None = Field(
        None, description="Specifies if the element and it's nested elements are hidden"
    )

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    @classmethod
    def shape_family(cls) -> type[BaseShape]:
        """The shape class of the ``shape`` field, for example ``NodeShape``."""
        annotation = cls.model_fields["shape"].annotation
        return next(
            t for t in get_args(annotation) or (annotation,) if t is not type(None)
        )

    @field_validator("shape", mode="before")
    @classmethod
    def load_shape_class(cls, value, info: ValidationInfo):
        """Load a shape from JSON as the class of its ``type`` (``shape_class``)."""
        if not isinstance(value, dict):
            return value
        model = shape_class(cls.shape_family(), value)
        if info.context == WIRE_CONTEXT:
            return from_wire(model, value)
        return model.model_validate(value, context=info.context)

    def get_shape(self) -> BaseShape:
        if self.shape is None:
            field = type(self).model_fields["shape"]
            if field.default_factory is not None:
                self.shape = field.get_default(
                    call_default_factory=True, validated_data=self.__dict__
                )
            else:
                self.shape = self.shape_family()()
        return cast("BaseShape", self.shape)


class NodeProperties(BaseProperties):
    shape: SerializeAsAny[NodeShape | None] = None

    def get_shape(self) -> NodeShape:
        return cast("NodeShape", super().get_shape())


class LabelProperties(BaseProperties):
    shape: SerializeAsAny[LabelShape | None] = None
    selectable: bool | None = Field(
        False, description="Specifies if label is individually selectable"
    )
    tooltip: str | None = Field(
        None,
        description=(
            "Hover text for the label (rendered as the label's svg <title>), "
            "e.g. the full text of a truncated label"
        ),
    )
    separator: bool | None = Field(
        None,
        description=(
            "Render a full-width horizontal rule across the parent node just "
            "above this label (e.g. a compartment header); unset/False draws nothing"
        ),
    )
    separatorGap: float | None = Field(
        None,
        ge=0,
        description=(
            "Distance in SVG pixels between this label's separator and its top; "
            "defaults to 1 when omitted"
        ),
    )

    def get_shape(self) -> LabelShape:
        return cast("LabelShape", super().get_shape())


class PortProperties(BaseProperties):
    shape: SerializeAsAny[PortShape | None] = None

    def get_shape(self) -> PortShape:
        return cast("PortShape", super().get_shape())


class EdgeProperties(BaseProperties):
    shape: SerializeAsAny[EdgeShape | None] = None

    def get_shape(self) -> EdgeShape:
        return cast("EdgeShape", super().get_shape())


IDElementT = TypeVar("IDElementT", bound="IDElement")


class IDElement(BaseModel, abc.ABC):
    #: an unknown key is a typo. ``from_wire`` ignores them in ELK JSON.
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(
        None,
        description=(
            "Must be a unique identifier for valid elk json. "
            "If not provided it can be generated."
        ),
    )

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return id(self) == id(other)

    _wire_id: str | None = PrivateAttr(None)
    _derived_id: bool = PrivateAttr(False)

    def __copy__(self):
        return self._as_new_object(super().__copy__())

    def __deepcopy__(self, memo=None):
        return self._as_new_object(super().__deepcopy__(memo))

    @staticmethod
    def _as_new_object(copied: IDElementT) -> IDElementT:
        """A copy (``copy``, ``deepcopy``, ``model_copy``) is a new element.

        It keeps an explicit ``id`` but never the original's wire id, which
        would put two elements with one id on the wire.
        """
        copied._wire_id = None
        return copied

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = handler(self)
        serialize_value(data, "id", self.wire_id(), info)
        return data

    def get_id(self) -> str | None:
        """The element's id: explicit, else the active ``Registry``'s, else ``None``.

        ``Registry`` is deprecated, and ipyelk never enters one: use ``wire_id``
        for the id that the element serializes with, which ``Document.index``
        pins. A Registry is seeded with that wire id, and an id it mints becomes
        the wire id, so the two agree whichever comes first.
        """
        if self.id is not None:
            return self.id
        return self._adopt_wire_id(Registry.get_id(self, self._wire_id))

    def _adopt_wire_id(self, el_id: str | None) -> str | None:
        if self._wire_id is None:
            self._wire_id = el_id
        return el_id

    def wire_id(self) -> str:
        """The id this element serializes with; never ``None``.

        ``get_id`` when that resolves, otherwise a UUID minted once per object,
        so repeated dumps agree with each other and with the ``sources`` /
        ``targets`` of edges that reference this element.  Does not assign
        ``id``: an element stays id-less until it is indexed.
        """
        el_id = self.get_id()
        if el_id is not None:
            return el_id
        return self._own_wire_id()

    def _own_wire_id(self) -> str:
        if self._wire_id is None:
            self._wire_id = new_id()
        return self._wire_id

    @property
    def derived_id(self) -> bool:
        """Whether ``id`` was derived (``Label.wrap``) and may be replaced on a clash."""
        return self._derived_id

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        display(JSON(self.model_dump()))


class BaseElement(IDElement, abc.ABC):
    labels: list[SerializeAsAny[Label]] = Field(default_factory=list)
    layoutOptions: LayoutOptions = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata, exclude=True)
    properties: SerializeAsAny[BaseProperties] = Field(default_factory=BaseProperties)

    model_config = ConfigDict(validate_assignment=True)

    def model_post_init(self, context) -> None:
        super().model_post_init(context)
        _claim_labels(self)

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        if name == "labels":
            _claim_labels(self)

    def add_class(self, *className: str) -> Self:
        """Adds a class to the top level element of the widget.

        Doesn't add the class if it already exists.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        dom_classes |= set(className)
        self.properties.cssClasses = " ".join(dom_classes).strip()
        return self

    def remove_class(self, *className: str) -> Self:
        """Removes a class from the top level element of the widget.

        Doesn't remove the class if it doesn't exist.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        self.properties.cssClasses = " ".join(
            dom_classes.difference(set(className))
        ).strip()
        return self

    @field_serializer(
        "labels", "ports", "children", "edges", mode="wrap", check_fields=False
    )
    def serialize_visible(self, elements, handler: SerializerFunctionWrapHandler):
        return handler([el for el in elements if not el.properties.hidden])


class ShapeElement(BaseElement, abc.ABC):
    """An element with a position and a size.

    After a layout, ``width`` and ``height`` hold the laid-out size
    (:meth:`set_laid_out`). The size serialized as the input to a layout
    (under ``exclude_layout``, as ``VisibilityPipe`` projects the tree) is, in
    this order: the size you assigned to the element, the size of its shape
    (``BaseShape.dimension``), the laid-out size. Any other serialization, for
    example the view's, carries the laid-out size. An element that has none of
    them serializes 0 without a shape. Assigning ``width`` or ``height`` makes
    that value the input, and ``None`` drops your assignment.
    """

    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    #: for each of ``width`` and ``height`` that holds a laid-out size, the
    #: size you had assigned before (``None`` for none); assigning the field
    #: removes its key
    _laid_out: dict[str, float | None] = PrivateAttr(default_factory=dict)

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        if name in {"width", "height"} and name in self._laid_out:
            # Shallow model copies share this dict; rebind to keep their inputs independent.
            self._laid_out = {k: v for k, v in self._laid_out.items() if k != name}

    def model_copy(
        self, *, update: Mapping[str, Any] | None = None, deep: bool = False
    ) -> Self:
        copied = super().model_copy(update=update, deep=deep)
        if update:
            # Pydantic applies updates without __setattr__ (or validation).
            copied._laid_out = {
                key: value
                for key, value in copied._laid_out.items()
                if key not in update
            }
        return copied

    def set_laid_out(self, width: float | None, height: float | None) -> Self:
        """Write the size the browser returned onto ``width`` and ``height``,
        remembering a size you assigned as the input to the next layout.
        """
        laid_out = dict(self._laid_out)
        for key, value in (("width", width), ("height", height)):
            if key not in laid_out:
                laid_out[key] = getattr(self, key)
            setattr(self, key, value)
        self._laid_out = laid_out
        return self

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = super().serialize_element(handler, info)
        shape = self.properties.shape
        laid_out = self._laid_out if exclude_layout.active else {}
        for key in ("width", "height"):
            own = getattr(self, key)
            value = laid_out.get(key, own)
            if value is None:
                value = shape.dimension(key) if shape else None
                if value is None:
                    value = own if key in laid_out else (None if shape else 0)
            if value is not None and value is not own:
                serialize_value(data, key, value, info)
        return data


class HierarchicalElement(ShapeElement, abc.ABC):
    _parent: Node | None = PrivateAttr(None)

    def set_parent(self, parent: Node | None = None):
        """Make ``parent`` the parent; ``None`` detaches.

        Raises ``ValueError``, naming both parents, if another node still
        holds this element in its ``children`` or ``ports``.
        """
        old = self._parent
        if parent is not None and old is not None and old is not parent:
            if any(el is self for el in (*old.children, *old.ports)):
                raise _second_parent(self, old, parent)
        self._parent = parent
        return self

    def get_parent(self) -> Node | None:
        return self._parent

    def set_key(self, key: str | None):
        assert self.properties.key is None or self.properties.key == key, (
            "Key has already been set"
        )
        self.properties.key = key
        return self


class EdgeSection(IDElement):
    startPoint: Point
    endPoint: Point
    bendPoints: list[Point] | None = Field(None, description="array of {x,y} pairs")
    incomingShape: str | None = Field(None, description="node and / or port identifier")
    outgoingShape: str | None = Field(None, description="node and / or port identifier")
    incomingSections: list[str] | None = Field(
        None, description="array of edge section identifiers"
    )
    outgoingSections: list[str] | None = Field(
        None, description="array of edge section identifiers"
    )


class Edge(BaseElement):
    properties: SerializeAsAny[EdgeProperties] = Field(default_factory=EdgeProperties)
    source: HierarchicalElement = Field(..., exclude=True)
    target: HierarchicalElement = Field(..., exclude=True)
    sections: list[EdgeSection] | None = Field(
        None,
        description="Captures the routing of an edge through a drawing",
    )

    @computed_field  # type: ignore[prop-decorator]  # Mypy cannot model decorated properties.
    @property
    def sources(self) -> list[str]:
        return [self.source.wire_id()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def targets(self) -> list[str]:
        return [self.target.wire_id()]

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.get_parent()
        v = self.target if isinstance(self.target, Node) else self.target.get_parent()
        return u, v

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = super().serialize_element(handler, info)
        if exclude_layout.active:
            serialize_value(data, "sections", None, info)
        return data


class Label(ShapeElement):
    text: str = Field(
        " ", description="Text shown for label"
    )  # completely empty strings exclude label in node sizing
    properties: SerializeAsAny[LabelProperties] = Field(default_factory=LabelProperties)

    def wrap(self, **kwargs) -> list[Label]:
        """Split text into individually laid-out labels with ``textwrap.wrap``.

        Keyword arguments are forwarded to ``textwrap.wrap``. Each line copies this
        label and its sub-labels (``metadata`` is shared). With several lines, an
        explicit id ``L`` becomes ``L#<line>``; indexing replaces such a derived id
        if another element already uses it.
        """
        lines = textwrap.wrap(self.text, **kwargs)
        suffix = len(lines) > 1
        return [
            self._copy_line(f"#{index}" if suffix else "", text=line)
            for index, line in enumerate(lines)
        ]

    def _copy_line(self, suffix: str, **update) -> Label:
        copy = self.model_copy(
            update={
                **update,
                "labels": [label._copy_line(suffix) for label in self.labels],
                "layoutOptions": dict(self.layoutOptions),
                "properties": self.properties.model_copy(deep=True),
            }
        )
        if suffix and self.id is not None:
            copy.id = f"{self.id}{suffix}"
            copy._derived_id = True
        return copy


class Port(HierarchicalElement):
    properties: SerializeAsAny[PortProperties] = Field(default_factory=PortProperties)

    def get_id(self) -> str | None:
        """``<parent id>.<own id>`` when the own id is Registry-assigned."""
        if self.id is not None:
            return self.id
        self_id = self._adopt_wire_id(Registry.get_id(self, self._wire_id))
        if self_id is None:
            return None
        return self._compose_id(self.get_parent(), self_id)

    def wire_id(self) -> str:
        port_id = self.get_id()
        if port_id is not None:
            return port_id
        return self._compose_id(self.get_parent(), self._own_wire_id())

    @staticmethod
    def _compose_id(parent: Node | None, self_id: str) -> str:
        if parent is None:
            return self_id
        return ".".join([parent.wire_id(), self_id])


class Node(HierarchicalElement):
    ports: list[SerializeAsAny[Port]] = Field(default_factory=list)
    children: list[SerializeAsAny[Node]] = Field(default_factory=list)
    edges: list[SerializeAsAny[Edge]] = Field(default_factory=list)
    properties: SerializeAsAny[NodeProperties] = Field(default_factory=NodeProperties)

    def model_post_init(self, context) -> None:
        super().model_post_init(context)
        for port in self.ports:
            port.set_parent(self)

        for child in self.children:
            child.set_parent(self)

    def __getattr__(self, key: str):
        try:
            # Pydantic hides this runtime hook from static type checkers.
            return super().__getattr__(key)  # type: ignore[misc]
        except AttributeError:
            if key.startswith("_"):
                raise
        try:
            return self.get_child(key)
        except NotFoundError:
            try:
                return self.get_port(key)
            except NotFoundError:
                pass
        raise AttributeError

    def add_child(self, child: Node, key: str | None = None) -> Node:
        self.children.append(child.set_parent(self).set_key(key))
        return child

    def remove_child(self, child: Node):
        """Remove the specified child from the children list as well as it's
        parent reference.

        :param child: Child node to remove
        :raises NotFoundError: If the child is not currently part of the
        node's children
        :return: The child that was removed
        """
        try:
            self.children.remove(child.set_parent())
        except ValueError as E:
            raise NotFoundError("Child element not found") from E
        return child

    def get_child(self, key: str) -> Node:
        """Method to iterate through children and find a match based on `key`

        :param key: key to match
        :raises NotFoundError: If unable to find a matching child
        :raises NotUniqueError: If found multiple children with the same key
        :return: matching child
        """
        matches = [child for child in self.children if key == child.properties.key]
        found = len(matches)
        if found == 1:
            return matches[0]
        if found == 0:
            raise NotFoundError("Child not found")
        raise NotUniqueError(f"{key} is not unique. Found {found} matching children.")

    def add_port(self, port: Port, key: str | None = None) -> Port:
        self.ports.append(port.set_parent(self).set_key(key))
        return port

    def get_port(self, key: str) -> Port:
        """Method to iterate through ports and find a match based on `key`

        :param key: key to match
        :raises NotFoundError: If unable to find a matching port
        :raises NotUniqueError: If found multiple ports with the same key
        :return: matching port
        """
        matches = [port for port in self.ports if key == port.properties.key]
        found = len(matches)
        if found == 1:
            return matches[0]
        if found == 0:
            raise NotFoundError("Port not found")
        raise NotUniqueError(f"{key} is not unique. Found {found} matching ports.")

    def clone(self, prefix: str) -> Self:
        """A copy of this node and everything under it, with fresh ids.

        Use it to reuse a fragment: one element cannot be under two parents.
        The copy of an element with the id ``X`` has the id ``"<prefix>.X"``,
        where ``X`` is the id that the element serializes with (its ``id``, or
        its ``wire_id``). So the same fragment and prefix always give the same
        ids, and every id of the copy is set. The copies have their own
        parents, layout options and ``properties``. An edge between two
        elements of the fragment connects their copies, and an edge to an
        element outside the fragment still connects that element. ``metadata``
        and the widget of a ``Widget`` shape are shared, not copied.
        """
        copies: dict[int, BaseElement] = {}
        cloned = cast("Self", _clone(self, prefix, copies))
        cloned._parent = None
        for el in copies.values():
            _claim_labels(el)
            if isinstance(el, Edge):
                el.source = cast(
                    "HierarchicalElement", copies.get(id(el.source), el.source)
                )
                el.target = cast(
                    "HierarchicalElement", copies.get(id(el.target), el.target)
                )
        return cloned

    def add_edge(
        self,
        source: Node | Port,
        target: Node | Port,
        cls: Type[Edge] = Edge,
    ) -> Edge:
        # for elk to layout correctly, edges must be owned by their lowest
        # common ancestor of the two endpoints the actual proper owner of the
        # edge may be calculated later
        edge = cls(source=source, target=target)
        self.edges.append(edge)
        return edge

    def __setattr__(self, key, value):
        if key.startswith("_") or key in type(self).model_fields:
            super().__setattr__(key, value)
        elif isinstance(value, Port):
            self.add_port(port=value, key=key)
        elif isinstance(value, Node):
            self.add_child(child=value, key=key)
        else:
            super().__setattr__(key, value)


#: label -> its parent element, both weakly: outside the model, so copies and
#: pickles of an element do not carry it
_LABEL_PARENTS: WeakKeyDictionary[Label, weakref.ref[BaseElement]] = WeakKeyDictionary()


def _claim_labels(parent: BaseElement) -> None:
    """Record ``parent`` as the parent of its labels.

    Raises ``ValueError``, naming both parents, for a label that another
    element still holds in its ``labels``. A label appended to ``labels`` in
    place is not checked here, but ``ValidationPipe`` still reports its id.
    """
    for label in parent.labels:
        ref = _LABEL_PARENTS.get(label)
        old = None if ref is None else ref()
        if old is not None and old is not parent:
            if any(el is label for el in old.labels):
                raise _second_parent(label, old, parent)
        _LABEL_PARENTS[label] = weakref.ref(parent)


def _second_parent(el: BaseElement, old: BaseElement, new: BaseElement) -> ValueError:
    def name(element: BaseElement) -> str:
        return f"{type(element).__name__} {element.wire_id()!r}"

    return ValueError(
        f"{name(el)} is already under {name(old)}, so it cannot also be under "
        f"{name(new)}. An element has one parent: detach it first, or use a copy "
        "(Node.clone(prefix) for a fragment, model_copy() for a label)."
    )


def _clone(el: BaseElement, prefix: str, copies: dict[int, BaseElement]) -> BaseElement:
    """Copy ``el`` and its sub elements for ``Node.clone``; ``copies`` maps the
    ``id()`` of each original to its copy.
    """
    shape = el.properties.shape
    shared = {id(shape.widget): shape.widget} if isinstance(shape, WidgetShape) else {}
    update: dict[str, Any] = {
        "id": f"{prefix}.{el.wire_id()}",
        "labels": [_clone(label, prefix, copies) for label in el.labels],
        "layoutOptions": dict(el.layoutOptions),
        "properties": copy.deepcopy(el.properties, shared),
    }
    if isinstance(el, Node):
        for name in ("ports", "children", "edges"):
            update[name] = [_clone(sub, prefix, copies) for sub in getattr(el, name)]
    if isinstance(el, Edge) and el.sections:
        update["sections"] = [
            section.model_copy(
                deep=True, update={"id": f"{prefix}.{section.wire_id()}"}
            )
            for section in el.sections
        ]
    cloned = el.model_copy(update=update)
    if isinstance(cloned, Node):
        for sub in (*cloned.ports, *cloned.children):
            sub._parent = cloned
    copies[id(el)] = cloned
    return cloned


Label.model_rebuild()
Port.model_rebuild()
Edge.model_rebuild()
BaseElement.model_rebuild()
Node.model_rebuild()
HierarchicalElement.model_rebuild()
EdgeShape.model_rebuild()
EdgeProperties.model_rebuild()
