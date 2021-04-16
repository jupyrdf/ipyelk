# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import textwrap
from typing import Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field, PrivateAttr

from .registry import Registry


def add_excluded_fields(kwargs: Dict, excluded: List) -> Dict:
    """Shim function to help manipulate excluded fields from the `dict`
    method"""

    exclude = kwargs.pop("exclude", None) or set()
    if isinstance(exclude, set):
        for i in excluded:
            exclude.add(i)
    else:
        raise TypeError(f"TODO handle other types of exclude e.g. {type(exclude)}")
    kwargs["exclude"] = exclude
    return kwargs


class ElementMetadata(BaseModel):
    pass


class ElementShape(BaseModel):
    type: Optional[str]
    use: Optional[str]
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class ElementProperties(BaseModel):
    cssClasses: str = ""
    shape: Optional[ElementShape]
    selectable: Optional[bool]


class EdgeShape(ElementShape):
    start: Optional[str]
    end: Optional[str]


class EdgeProperties(ElementProperties):
    shape: Optional[EdgeShape]


class BaseElement(BaseModel):
    id: Optional[str] = Field(None)  # required for final elk json schema
    labels: List["Label"] = Field(default_factory=list)
    properties: ElementProperties = Field(default_factory=ElementProperties)
    layoutOptions: Dict = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata)

    class Config:
        copy_on_model_validation = False

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return id(self) == id(other)

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

    def dict(self, **kwargs) -> Dict:
        """Shimming in the ability to have excluded fields by default. This
        should be removeable in future versions of pydantic
        """
        excluded = getattr(self.Config, "excluded", [])
        if excluded:
            kwargs = add_excluded_fields(kwargs, excluded)
        data = super().dict(**kwargs)
        data["id"] = self._get_id()
        return data

    def _get_id(self) -> Optional[str]:
        if self.id is None:
            return Registry.get_id(self)
        return self.id


class ShapeElement(BaseElement):
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


class UnionNodePort(ShapeElement):
    key: Optional[str] = Field(
        None,
        description="Non-elkjson schema property used to provide lookup from parent",
        exclude=True,
    )
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
        assert self.key is None or self.key == key, "Key has already been set"
        self.key = key
        return self


class Edge(BaseElement):
    properties: EdgeProperties = Field(default_factory=EdgeProperties)
    source: UnionNodePort = Field(...)
    target: UnionNodePort = Field(...)

    class Config:
        excluded = ["source", "target"]

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.get_parent()
        v = self.target if isinstance(self.target, Node) else self.target.get_parent()
        return u, v

    def dict(self, **kwargs):
        data = super().dict(**kwargs)

        if isinstance(self.source, Port):
            data["source"] = Registry.get_id(self.source.get_parent())
            data["sourcePort"] = Registry.get_id(self.source)
        else:
            data["source"] = Registry.get_id(self.source)
        if isinstance(self.target, Port):
            data["target"] = Registry.get_id(self.target.get_parent())
            data["targetPort"] = Registry.get_id(self.target)
        else:
            data["target"] = Registry.get_id(self.target)

        return data


class Label(ShapeElement):
    text: str = " "  # completely empty strings exclude label in node sizing
    properties: ElementProperties = Field(
        default_factory=lambda: ElementProperties(selectable=False)
    )

    def wrap(self, **kwargs) -> List["Label"]:
        data = self.dict()
        return [
            Label(**{**data, "text": line})
            for line in textwrap.wrap(self.text, **kwargs)
        ]


class Port(UnionNodePort):
    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["parent", "key"]

    def dict(self, **kwargs):
        if self.properties.shape is None:
            self.properties.shape = ElementShape(type="port")
        else:
            if self.properties.shape.type is None:
                self.properties.shape.type = "port"
            assert "port" in self.properties.shape.type
        data = super().dict(**kwargs)
        return data

    def _get_id(self) -> Optional[str]:
        if self.id is None:
            parent_id = Registry.get_id(self.get_parent())
            self_id = Registry.get_id(self)
            if parent_id is not None and self_id is not None:
                return ".".join([parent_id, self_id])
        return self.id


class Node(UnionNodePort):
    ports: List[Port] = Field(default_factory=list)
    children: List["Node"] = Field(default_factory=list)
    edges: Set[Edge] = Field(default_factory=set)

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["metadata", "parent", "key"]
        to_list = ["edges"]

    def __init__(self, **data):
        super().__init__(**data)
        # for port in self.ports:
        #     port.set_parent(self)

        # for child in self.children:
        #     child.set_parent(self)

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

        for key in self.Config.to_list:
            if key in data:
                value = data[key]
                if isinstance(value, (set,)):
                    value = list(value)
                elif isinstance(value, dict):
                    value = list(data[key].values())
                else:
                    raise TypeError(f"Need to handle converting {type(value)}")
                data[key] = value
        return data

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
        :raises NonUniqueKeyError: If found multiple children with the same key
        :return: matching child
        """
        matches = []
        for child in self.children:
            if key == child.key:
                matches.append(child)
        found = len(matches)
        if found == 1:
            return matches[0]
        elif found == 0:
            raise NotFoundError("Child not found")
        else:
            raise NonUniqueKeyError(
                f"{key} is not unique. Found {found} matching children."
            )

    def add_port(self, port: Port, key: Optional[str] = None) -> Port:
        self.ports.append(port.set_parent(self).set_key(key))
        return port

    def get_port(self, key: str) -> Port:
        """Method to iterate through ports and find a match based on `key`

        :param key: key to match
        :raises NotFoundError: If unable to find a matching port
        :raises NonUniqueKeyError: If found multiple ports with the same key
        :return: matching port
        """
        matches = []
        for port in self.ports:
            if key == port.key:
                matches.append(port)
        found = len(matches)
        if found == 1:
            return matches[0]
        elif found == 0:
            raise NotFoundError("Port not found")
        else:
            raise NonUniqueKeyError(
                f"{key} is not unique. Found {found} matching ports."
            )

    def add_edge(
        self,
        source: Union["Node", Port],
        target: Union["Node", Port],
        cls: Type[Edge] = Edge,
    ) -> Edge:
        # for elk to layout correctly, edges must be owned by some common
        # ancestor of the two endpoints the actual owner of the edge will be
        # calculated later
        edge = cls(source=source, target=target)
        self.edges.add(edge)
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


class NotFoundError(Exception):
    pass


class NonUniqueKeyError(Exception):
    pass


Label.update_forward_refs()
Port.update_forward_refs()
Edge.update_forward_refs()
BaseElement.update_forward_refs()
Node.update_forward_refs()
UnionNodePort.update_forward_refs()
EdgeShape.update_forward_refs()
EdgeProperties.update_forward_refs()
