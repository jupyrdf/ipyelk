# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import textwrap
from typing import ClassVar, Dict, List, Optional, Set, Type, Union

from pydantic import BaseModel, Field

from ..diagram.elk_model import strip_none
from ..diagram.symbol import Symbol
from ..util import merge
from .registry import Registry


class ElementMetadata(BaseModel):
    pass


class ElementShape(BaseModel):
    use: Optional[str]
    start: Optional[str]
    end: Optional[str]
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]


class ElementProperties(BaseModel):
    cssClasses: Optional[str]
    type: Optional[str]
    shape: Optional[ElementShape]
    selectable: Optional[bool]


class BaseElement(BaseModel):
    labels: List["Label"] = Field(default_factory=list)
    properties: Dict = Field(
        default_factory=dict
    )  # TODO convert to use `ElementProperties`
    layoutOptions: Dict = Field(default_factory=dict)
    metadata: ElementMetadata = Field(default_factory=ElementMetadata)
    selectable: bool = True
    _dom_classes: List[str] = Field(init=False, repr=False, default_factory=list)
    _css_classes: ClassVar[List[str]] = []

    class Config:
        copy_on_model_validation = False

    def __init__(self, **data):
        super().__init__(**data)
        classes = self._css_classes or []
        for css_class in classes:
            self.add_class(css_class)

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return id(self) == id(other)

    def to_json(self):
        raise NotImplementedError("Subclasses should implement")

    def add_class(self, className: str) -> "BaseElement":
        """
        Adds a class to the top level element of the widget.

        Doesn't add the class if it already exists.
        """
        dom_classes = self.properties.get("cssClasses", "").split(" ")
        if className not in dom_classes:
            dom_classes = list(dom_classes) + [className]
        self.properties["cssClasses"] = " ".join(dom_classes).strip()
        return self

    def remove_class(self, className: str) -> "BaseElement":
        """
        Removes a class from the top level element of the widget.

        Doesn't remove the class if it doesn't exist.
        """
        dom_classes = self.properties.get("cssClasses", "").split(" ")
        if className in dom_classes:
            self.properties["cssClasses"] = " ".join(
                [c for c in dom_classes if c != className]
            ).strip()
        return self


class ShapeElement(BaseElement):
    shape: Optional[Symbol] = None

    def to_json(self):
        if isinstance(self.shape, Symbol):
            data = self.shape.to_json(id=Registry.get_id(self))
        else:
            data = {"id": Registry.get_id(self)}
        labels = data["labels"] = data.get("labels", [])
        labels.extend([label.to_json() for label in self.labels])
        props = merge(self.properties, data.get("properties", {}))
        if props is None:
            props = {}
        props["selectable"] = self.selectable
        data["properties"] = props
        data["layoutOptions"] = merge(self.layoutOptions, data.get("layoutOptions", {}))

        return strip_none(data)


class UnionNodePort(ShapeElement):
    pass


class Edge(BaseElement):
    shape_end: Optional[str] = None  # TODO maybe should be a ConnectorDef object
    shape_start: Optional[str] = None

    source: UnionNodePort = None
    target: UnionNodePort = None

    def to_json(self):
        props = self.properties
        shape = props["shape"] = props.get("shape", {})
        props["selectable"] = self.selectable
        for key, connector in zip(["start", "end"], [self.shape_start, self.shape_end]):
            if connector:
                shape[key] = connector

        data = {
            "id": Registry.get_id(self),
            "properties": props,
            "layoutOptions": self.layoutOptions,
            "labels": [label.to_json() for label in self.labels],
        }
        if isinstance(self.source, Port):
            data["sourcePort"] = Registry.get_id(self.source)
        if isinstance(self.target, Port):
            data["targetPort"] = Registry.get_id(self.target)
        return data

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source.parent
        v = self.target if isinstance(self.target, Node) else self.target.parent
        return u, v


class Label(ShapeElement):
    text: str = " "  # completely empty strings exclude label in node sizing
    selectable: bool = False

    def to_json(self):
        data = super().to_json()
        data["text"] = self.text
        return data

    def wrap(self, **kwargs) -> List["Label"]:
        data = self.to_json()
        return [
            Label(**{**data, "text": line})
            for line in textwrap.wrap(self.text, **kwargs)
        ]


class Port(UnionNodePort):
    parent: Optional["Node"] = Field(default=None)

    class Config:
        copy_on_model_validation = False

    def to_json(self):
        data = super().to_json()
        parent_id = Registry.get_id(self.parent)
        self_id = Registry.get_id(self)
        data["id"] = ".".join([parent_id, self_id])
        if "properties" not in data:
            data["properties"] = {}
        data["properties"]["type"] = "port"
        return data


class Node(UnionNodePort):
    ports: Dict[str, Port] = Field(default_factory=dict)
    children: Dict[str, "Node"] = Field(default_factory=dict)

    edges: Set[Edge] = Field(
        init=False, repr=False, default_factory=set
    )  # could be a set?

    class Config:
        copy_on_model_validation = False

    def __init__(self, **data):
        super().__init__(**data)
        for key, port in self.ports.items():
            port_parent(self, port)

    def __getattr__(self, key):
        if key in self.children:
            return self.children.get(key)
        if key in self.ports:
            return self.ports.get(key)
        shape_ports = getattr(self.shape, "ports", {})
        if key in shape_ports:
            return self.add_port(key=key, port=Port())
        # TODO decide on bad magic to create a port if it doesn't exist?
        raise AttributeError

    def to_json(self):
        data = super().to_json()
        shape_ports = {p["id"].split(".")[-1]: p for p in data.get("ports", [])}
        ports = {}

        # merge shape ports and ports defined on the element
        for key, port in shape_ports.items():
            if key in self.ports:
                port = merge(self.ports[key].to_json(), port)
            ports[key] = port

        # add additional ports only defined on he element
        for key, port in self.ports.items():
            if key not in ports:
                ports[key] = port.to_json()
        data["ports"] = ports.values()
        return strip_none(data)

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
