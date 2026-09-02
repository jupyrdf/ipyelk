# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import abc
import textwrap
from typing import Type

from pydantic.v1 import BaseModel, Field, PrivateAttr

from ..exceptions import NotFoundError, NotUniqueError
from .common import CounterContextManager, add_excluded_fields
from .registry import Registry
from .shapes import BaseShape, EdgeShape, LabelShape, NodeShape, Point, PortShape

exclude_hidden = CounterContextManager()
exclude_layout = CounterContextManager()


def merge_excluded(cls: Type[BaseModel], *fields: str) -> list[str]:
    base = set(getattr(cls.Config, "excluded", []))
    return list(base | set(fields))


class ElementMetadata(BaseModel):
    """An empty metadata structure, subclass and add your own attributes using
    pydantic to have validated element metadata. This metadata will not be used
    for layout purposes but potentially useful for maintaining annotations about
    the elements for downstream applications.
    """


class BaseProperties(BaseModel):
    cssClasses: str = Field("", description="whitespace separated list of css classes")
    shape: BaseShape | None
    key: str | None = Field(
        None, description="Used to provide lookup functionality from owner"
    )
    hidden: bool | None = Field(
        None, description="Specifies if the element and it's nested elements are hidden"
    )

    class Config:
        copy_on_model_validation = "none"
        validate_assignment = True

    def get_shape(self) -> BaseShape:
        if self.shape is None:
            field = self.__fields__["shape"]
            cls = (
                field.default_factory
                if field.default_factory is not None
                else field.type_
            )
            self.shape = cls()
        return self.shape


class NodeProperties(BaseProperties):
    shape: NodeShape | None

    def get_shape(self) -> NodeShape:
        return super().get_shape()


class LabelProperties(BaseProperties):
    shape: LabelShape | None
    selectable: bool | None = Field(
        False, description="Specifies if label is individually selectable"
    )

    def get_shape(self) -> LabelShape:
        return super().get_shape()


class PortProperties(BaseProperties):
    shape: PortShape | None

    def get_shape(self) -> PortShape:
        return super().get_shape()


class EdgeProperties(BaseProperties):
    shape: EdgeShape | None

    def get_shape(self) -> EdgeShape:
        return super().get_shape()


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

    def dict(self, **kwargs) -> dict:
        """Shimming in the ability to have excluded fields by default. This
        should be removeable in future versions of pydantic
        """
        excluded = getattr(self.Config, "excluded", [])
        if excluded:
            kwargs = add_excluded_fields(kwargs, excluded)
        data = super().dict(**kwargs)
        data["id"] = self.get_id()

        # mechanism to convert some fields to a list representation if needed
        for key in getattr(self.Config, "to_list", []):
            if key in data:
                value = data[key]
                if isinstance(value, (set, list, tuple)):
                    value = list(value)
                elif isinstance(value, dict):
                    value = list(data[key].values())
                else:
                    raise TypeError(f"Need to handle converting {key}:{type(value)}")
                data[key] = value

        return data

    def get_id(self) -> str:
        if self.id is not None:
            return self.id
        return Registry.get_id(self)

    def _repr_mimebundle_(self, **kwargs):
        from IPython.display import JSON, display

        display(JSON(self.dict()))


class BaseElement(IDElement, abc.ABC):
    labels: list[Label] = Field(default_factory=list)
    layoutOptions: dict = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata)
    properties: BaseProperties = Field(default_factory=BaseProperties)

    class Config:
        copy_on_model_validation = "none"
        validate_assignment = True
        excluded = merge_excluded(IDElement, "metadata", "labels")

    def add_class(self, *className: str) -> BaseElement:
        """Adds a class to the top level element of the widget.

        Doesn't add the class if it already exists.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        dom_classes |= set(className)
        self.properties.cssClasses = " ".join(dom_classes).strip()
        return self

    def remove_class(self, *className: str) -> BaseElement:
        """Removes a class from the top level element of the widget.

        Doesn't remove the class if it doesn't exist.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        self.properties.cssClasses = " ".join(
            dom_classes.difference(set(className))
        ).strip()
        return self

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["labels"] = list_visible(self.labels, **kwargs)
        return data


def list_visible(els: list[BaseElement], **kwargs):
    return [el.dict(**kwargs) for el in els if not el.properties.hidden]


class ShapeElement(BaseElement, abc.ABC):
    x: float | None
    y: float | None
    width: float | None
    height: float | None

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        # potentially set width and height if there is a shape defined in the
        # properties
        width = 0
        height = 0
        if self.properties.shape:
            shape = self.properties.shape
            width = shape.width
            height = shape.height
        # update width if not set
        if data.get("width", None) is None and width is not None:
            data["width"] = width
        # update height if not set
        if data.get("height", None) is None and height is not None:
            data["height"] = height

        # if exclude_layout.active:
        #     for attr in ["x", "y", "width", "height"]:
        #         data[attr] = None
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
    bendPoints: list[Point] = Field(None, description="array of {x,y} pairs")
    incomingShape: str | None = Field(None, description="node and / or port identifier")
    outgoingShape: str | None = Field(None, description="node and / or port identifier")
    incomingSections: list[str] | None = Field(
        None, description="array of edge section identifiers"
    )
    outgoingSections: list[str] | None = Field(
        None, description="array of edge section identifiers"
    )


class Edge(BaseElement):
    properties: EdgeProperties = Field(default_factory=EdgeProperties)
    source: HierarchicalElement = Field(...)
    target: HierarchicalElement = Field(...)
    sections: list[EdgeSection] | None = Field(
        description="Captures the routing of an edge through a drawing",
    )

    class Config:
        copy_on_model_validation = "none"
        validate_assignment = True
        excluded = merge_excluded(BaseElement, "source", "target")

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.get_parent()
        v = self.target if isinstance(self.target, Node) else self.target.get_parent()
        return u, v

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["sources"] = [self.source.get_id()]
        data["targets"] = [self.target.get_id()]
        if exclude_layout.active:
            for attr in ["sections"]:
                data[attr] = None
        return data


class Label(ShapeElement):
    text: str = Field(
        " ", description="Text shown for label"
    )  # completely empty strings exclude label in node sizing
    properties: LabelProperties = Field(default_factory=LabelProperties)

    def wrap(self, **kwargs) -> list[Label]:
        data = self.dict()
        return [
            Label(**{**data, "text": line})
            for line in textwrap.wrap(self.text, **kwargs)
        ]


class Port(HierarchicalElement):
    properties: PortProperties = Field(default_factory=PortProperties)

    class Config:
        copy_on_model_validation = "none"
        validate_assignment = True

        # non-pydantic configs
        excluded = merge_excluded(HierarchicalElement)

    def get_id(self) -> str | None:
        if self.id is None:
            parent_id = Registry.get_id(self.get_parent())
            self_id = Registry.get_id(self)
            if parent_id is not None and self_id is not None:
                return ".".join([parent_id, self_id])
        return self.id


class Node(HierarchicalElement):
    ports: list[Port] = Field(default_factory=list)
    children: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    properties: NodeProperties = Field(default_factory=NodeProperties)

    class Config:
        copy_on_model_validation = "none"
        validate_assignment = True

        # non-pydantic configs
        excluded = merge_excluded(HierarchicalElement, "ports", "children", "edges")

    def __init__(self, **data):  # type: ignore
        super().__init__(**data)
        for port in self.ports:
            port.set_parent(self)

        for child in self.children:
            child.set_parent(self)

    def __getattr__(self, key: str):
        try:
            return self.get_child(key)
        except NotFoundError:
            try:
                return self.get_port(key)
            except NotFoundError:
                pass
        raise AttributeError

    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        data["ports"] = list_visible(self.ports, **kwargs)
        data["children"] = list_visible(self.children, **kwargs)
        data["edges"] = list_visible(self.edges, **kwargs)
        return data

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
        if key == "_parent":
            super().__setattr__(key, value)
        elif isinstance(value, Port):
            self.add_port(port=value, key=key)
        elif isinstance(value, Node):
            self.add_child(child=value, key=key)
        else:
            super().__setattr__(key, value)


Label.update_forward_refs()
Port.update_forward_refs()
Edge.update_forward_refs()
BaseElement.update_forward_refs()
Node.update_forward_refs()
HierarchicalElement.update_forward_refs()
EdgeShape.update_forward_refs()
EdgeProperties.update_forward_refs()
