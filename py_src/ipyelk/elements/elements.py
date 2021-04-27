# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import abc
import textwrap
from typing import Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, PrivateAttr

from ..exceptions import NotFoundError, NotUniqueError
from .common import add_excluded_fields
from .registry import Registry
from .shapes import BaseShape, EdgeShape, LabelShape, NodeShape, Point, PortShape


class ElementMetadata(BaseModel):
    """An empty metadata structure, subclass and add your own attributes using
    pydantic to have validated element metadata. This metadata will not be used
    for layout purposes but potentially useful for maintaining annotations about
    the elements for downstream applications.
    """


class BaseProperties(BaseModel):
    cssClasses: str = Field("", description="whitespace separated list of css classes")
    shape: Optional[BaseShape]
    key: Optional[str] = Field(
        None, description="Used to provide lookup functionality from owner"
    )

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
    shape: Optional[NodeShape]
    hidden: Optional[bool] = Field(
        None, description="Specifies if the node and it's children are hidden"
    )

    def get_shape(self) -> NodeShape:
        return super().get_shape()


class LabelProperties(BaseProperties):
    shape: Optional[LabelShape]
    selectable: Optional[bool] = Field(
        False, description="Specifies if label is individually selectable"
    )

    def get_shape(self) -> LabelShape:
        return super().get_shape()


class PortProperties(BaseProperties):
    shape: Optional[PortShape]

    def get_shape(self) -> PortShape:
        return super().get_shape()


class EdgeProperties(BaseProperties):
    shape: Optional[EdgeShape]

    def get_shape(self) -> EdgeShape:
        return super().get_shape()


class IDElement(BaseModel, abc.ABC):
    id: Optional[str] = Field(
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

    def dict(self, **kwargs) -> Dict:
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


class BaseElement(IDElement, abc.ABC):
    labels: List["Label"] = Field(default_factory=list)
    layoutOptions: Dict = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata)
    properties: BaseProperties = Field(default_factory=BaseProperties)

    class Config:
        copy_on_model_validation = False

        excluded = ["metadata"]

    def add_class(self, className: str) -> "BaseElement":
        """
        Adds a class to the top level element of the widget.

        Doesn't add the class if it already exists.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        dom_classes.add(className)
        self.properties.cssClasses = " ".join(dom_classes).strip()
        return self

    def remove_class(self, className: str) -> "BaseElement":
        """
        Removes a class from the top level element of the widget.

        Doesn't remove the class if it doesn't exist.
        """
        dom_classes = set(self.properties.cssClasses.split(" "))
        self.properties.cssClasses = " ".join(
            dom_classes.difference(set([className]))
        ).strip()
        return self


class ShapeElement(BaseElement, abc.ABC):
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]

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

        return data


class HierarchicalElement(ShapeElement, abc.ABC):
    _parent: Optional["Node"] = PrivateAttr(None)

    def set_parent(self, parent: Optional["Node"]):
        assert (
            self._parent is None or self._parent is parent
        ), "Incoming port owned by different node"
        self._parent = parent
        return self

    def get_parent(self) -> Optional["Node"]:
        return self._parent

    def set_key(self, key: Optional[str]):
        assert (
            self.properties.key is None or self.properties.key == key
        ), "Key has already been set"
        self.properties.key = key
        return self


class EdgeSection(IDElement):
    startPoint: Point
    endPoint: Point
    bendPoints: List[Point] = Field(None, description="array of {x,y} pairs")
    incomingShape: Optional[str] = Field(
        None, description="node and / or port identifier"
    )
    outgoingShape: Optional[str] = Field(
        None, description="node and / or port identifier"
    )
    incomingSections: Optional[List[str]] = Field(
        None, description="array of edge section identifiers"
    )
    outgoingSections: Optional[List[str]] = Field(
        None, description="array of edge section identifiers"
    )


class Edge(BaseElement):
    properties: EdgeProperties = Field(default_factory=EdgeProperties)
    source: HierarchicalElement = Field(...)
    target: HierarchicalElement = Field(...)
    sections: List[EdgeSection] = Field(
        default_factory=list,
        description="Captures the routing of an edge through a drawing",
    )

    class Config:
        excluded = ["metadata", "source", "target"]

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.get_parent()
        v = self.target if isinstance(self.target, Node) else self.target.get_parent()
        return u, v

    def dict(self, **kwargs):
        data = super().dict(**kwargs)

        data["sources"] = [self.source.get_id()]
        data["targets"] = [self.target.get_id()]

        # if isinstance(self.source, Port):
        #     print("sourePorting")
        #     data["sources"] = [self.source.get_parent().get_id()]
        #     data["sourcePort"] = self.source.get_id()
        # else:
        #     data["sources"] = [self.source.get_id()]
        # if isinstance(self.target, Port):
        #     print("targetPorting")
        #     data["targets"] = [self.target.get_parent().get_id()]
        #     data["targetPort"] = self.target.get_id()
        # else:
        #     data["targets"] = [self.target.get_id()]
        return data


class Label(ShapeElement):
    text: str = Field(
        " ", description="Text shown for label"
    )  # completely empty strings exclude label in node sizing
    properties: LabelProperties = Field(default_factory=LabelProperties)

    def wrap(self, **kwargs) -> List["Label"]:
        data = self.dict()
        return [
            Label(**{**data, "text": line})
            for line in textwrap.wrap(self.text, **kwargs)
        ]


class Port(HierarchicalElement):
    properties: PortProperties = Field(default_factory=PortProperties)

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["metadata", "parent", "key"]

    def get_id(self) -> Optional[str]:
        if self.id is None:
            parent_id = Registry.get_id(self.get_parent())
            self_id = Registry.get_id(self)
            if parent_id is not None and self_id is not None:
                return ".".join([parent_id, self_id])
        return self.id


class Node(HierarchicalElement):
    ports: List[Port] = Field(default_factory=list)
    children: List["Node"] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    properties: NodeProperties = Field(default_factory=NodeProperties)

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["metadata", "parent", "key"]

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

    def add_child(self, child: "Node", key: Optional[str] = None) -> "Node":
        self.children.append(child.set_parent(self).set_key(key))
        return child

    def remove_child(self, child: "Node"):
        """Remove the specified child from the children list as well as it's
        parent reference.

        :param child: Child node to remove
        :raises NotFoundError: If the child is not currently part of the
        node's children
        :return: The child that was removed
        """
        try:
            self.children.remove(child)
            child.set_parent(None)
        except ValueError as E:
            raise NotFoundError("Child element not found") from E
        return child

    def get_child(self, key: str) -> "Node":
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
        elif found == 0:
            raise NotFoundError("Child not found")
        else:
            raise NotUniqueError(
                f"{key} is not unique. Found {found} matching children."
            )

    def add_port(self, port: Port, key: Optional[str] = None) -> Port:
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
        elif found == 0:
            raise NotFoundError("Port not found")
        else:
            raise NotUniqueError(f"{key} is not unique. Found {found} matching ports.")

    def add_edge(
        self,
        source: Union["Node", Port],
        target: Union["Node", Port],
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
