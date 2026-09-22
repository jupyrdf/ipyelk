# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import abc
import textwrap
from typing import Type, cast, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SerializationInfo,
    SerializeAsAny,
    SerializerFunctionWrapHandler,
    computed_field,
    field_serializer,
    model_serializer,
)
from typing_extensions import Self

from ..exceptions import NotFoundError, NotUniqueError
from .common import CounterContextManager, serialize_value
from .registry import Registry, new_id
from .shapes import BaseShape, EdgeShape, LabelShape, NodeShape, Point, PortShape

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

    model_config = ConfigDict(validate_assignment=True)

    def get_shape(self) -> BaseShape:
        if self.shape is None:
            field = type(self).model_fields["shape"]
            if field.default_factory is not None:
                self.shape = field.get_default(
                    call_default_factory=True, validated_data=self.__dict__
                )
            else:
                cls = next(t for t in get_args(field.annotation) if t is not type(None))
                self.shape = cls()
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


class IDElement(BaseModel, abc.ABC):
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

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = handler(self)
        serialize_value(data, "id", self.wire_id(), info)
        return data

    def get_id(self) -> str | None:
        """The element's id: explicit, else the active ``Registry``'s, else ``None``.

        The Registry is seeded with the id this element has already put on the
        wire (see ``wire_id``), so the id first serialised is the id the index
        is later keyed by.
        """
        if self.id is not None:
            return self.id
        return Registry.get_id(self, self._wire_id)

    def wire_id(self) -> str:
        """The id this element serialises with; never ``None``.

        ``get_id`` when that resolves, otherwise a uuid minted once per object,
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

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        display(JSON(self.model_dump()))


class BaseElement(IDElement, abc.ABC):
    labels: list[SerializeAsAny[Label]] = Field(default_factory=list)
    layoutOptions: dict = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata, exclude=True)
    properties: SerializeAsAny[BaseProperties] = Field(default_factory=BaseProperties)

    model_config = ConfigDict(validate_assignment=True)

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
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        data = super().serialize_element(handler, info)
        shape = self.properties.shape
        for key in ("width", "height"):
            if getattr(self, key) is None:
                value = shape.dimension(key) if shape else 0
                if value is not None:
                    serialize_value(data, key, value, info)
        return data


class HierarchicalElement(ShapeElement, abc.ABC):
    _parent: Node | None = PrivateAttr(None)

    def set_parent(self, parent: Node | None = None):
        if parent is not None:
            assert self._parent is None or self._parent is parent, (
                f"{self.__class__.__name__} owned by different node"
            )
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
        data = self.model_dump()
        if self.id is None:
            # the dump carries this label's wire id; the lines must not share it
            data.pop("id", None)
        return [
            Label(**{**data, "text": line})
            for line in textwrap.wrap(self.text, **kwargs)
        ]


class Port(HierarchicalElement):
    properties: SerializeAsAny[PortProperties] = Field(default_factory=PortProperties)

    def get_id(self) -> str | None:
        """``<parent id>.<own id>`` when the own id is Registry-assigned."""
        if self.id is not None:
            return self.id
        self_id = Registry.get_id(self, self._wire_id)
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
        # TODO uniqueness of edge?
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


Label.model_rebuild()
Port.model_rebuild()
Edge.model_rebuild()
BaseElement.model_rebuild()
Node.model_rebuild()
HierarchicalElement.model_rebuild()
EdgeShape.model_rebuild()
EdgeProperties.model_rebuild()
