# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import textwrap
from typing import Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field

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
    pass


class Edge(BaseElement):
    properties: EdgeProperties = Field(default_factory=EdgeProperties)
    source: UnionNodePort = Field(...)
    target: UnionNodePort = Field(...)

    class Config:
        excluded = ["source", "target"]

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.parent
        v = self.target if isinstance(self.target, Node) else self.target.parent
        return u, v

    def dict(self, **kwargs):
        data = super().dict(**kwargs)

        if isinstance(self.source, Port):
            data["source"] = Registry.get_id(self.source.parent)
            data["sourcePort"] = Registry.get_id(self.source)
        else:
            data["source"] = Registry.get_id(self.source)
        if isinstance(self.target, Port):
            data["target"] = Registry.get_id(self.target.parent)
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
    parent: Optional["Node"] = Field(default=None, exclude=True)

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["parent"]

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
            parent_id = Registry.get_id(self.parent)
            self_id = Registry.get_id(self)
            if parent_id is not None and self_id is not None:
                return ".".join([parent_id, self_id])
        return self.id


class Node(UnionNodePort):
    ports: Dict[str, Port] = Field(default_factory=dict)
    children: Dict[str, "Node"] = Field(default_factory=dict)
    edges: Set[Edge] = Field(default_factory=set)

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = ["metadata"]
        to_list = ["children", "ports", "edges"]

    def __init__(self, **data):
        super().__init__(**data)
        for key, port in self.ports.items():
            port_parent(self, port)

    def __getattr__(self, key):
        if key in self.children:
            return self.children.get(key)
        if key in self.ports:
            return self.ports.get(key)
        # TODO decide on bad magic to create a port if it doesn't exist?
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

    def add_child(self, child: "Node", key: str) -> "Node":
        self.children[key] = child
        return child

    def remove_child(self, child: "Node", key: str = ""):
        for key, value in self.children.items():
            if value is child:
                break
        else:
            raise ValueError("Child element not found")
        self.children.pop(key)
        return child

    def add_port(self, port: Port, key) -> Port:
        self.ports[key] = port_parent(self, port)
        return port

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
        if isinstance(value, Port):
            self.add_port(port=value, key=key)
        elif isinstance(value, Node):
            self.add_child(child=value, key=key)
        else:
            super().__setattr__(key, value)


def port_parent(node: Node, port: Port) -> Port:
    assert (
        port.parent is None or port.parent is node
    ), "Incoming port owned by different node"
    port.parent = node
    return port


Label.update_forward_refs()
Port.update_forward_refs()
Edge.update_forward_refs()
BaseElement.update_forward_refs()
Node.update_forward_refs()
UnionNodePort.update_forward_refs()
EdgeShape.update_forward_refs()
EdgeProperties.update_forward_refs()
