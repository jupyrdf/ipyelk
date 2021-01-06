# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Union

from ...diagram.elk_model import strip_none
from ...diagram.symbol import Symbol
from ...transform import merge
from .registry import Registry


@dataclass
class Element:
    labels: List["Label"] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)
    layoutOptions: Dict = field(default_factory=dict)

    def to_json(self):
        raise NotImplementedError("Subclasses should implement")

    def __hash__(self):
        return id(self)


@dataclass
class Edge(Element):
    shape_end: Optional[Symbol] = None
    shape_start: Optional[Symbol] = None

    source: Union["Node", "Port"] = None
    target: Union["Node", "Port"] = None

    def to_json(self):
        data = {
            "id": Registry.get_id(self),
            "properties": {},
            "layoutOptions": {},
            "labels": [],
        }
        if isinstance(self.source, Port):
            data["sourcePort"] = Registry.get_id(self.source)
        if isinstance(self.target, Port):
            data["targetPort"] = Registry.get_id(self.target)
        return data

    def points(self):
        u = self.source if isinstance(self.source, Node) else self.source._parent
        v = self.target if isinstance(self.target, Node) else self.target._parent
        return u, v

    def __hash__(self):
        return id(self)


@dataclass
class ShapeElement(Element):
    shape: Optional[Symbol] = None

    def to_json(self):
        if isinstance(self.shape, Symbol):
            data = self.shape.to_json(id=Registry.get_id(self))
        else:
            data = {"id": Registry.get_id(self)}
        labels = data["labels"] = data.get("labels", [])
        labels.extend([label.to_json() for label in self.labels])
        data["properties"] = merge(self.properties, data.get("properties", {}))
        data["layoutOptions"] = merge(self.layoutOptions, data.get("layoutOptions", {}))

        return strip_none(data)

    def __hash__(self):
        return id(self)


@dataclass
class Port(ShapeElement):
    _parent: Optional["Node"] = field(init=False, repr=False, default=None)

    def to_json(self):
        data = super().to_json()
        parent_id = Registry.get_id(self._parent)
        self_id = Registry.get_id(self)
        data["id"] = ".".join([parent_id, self_id])
        return data

    def __hash__(self):
        return id(self)


@dataclass
class Label(ShapeElement):
    text: str = " "  # completely empty strings exclude label in node sizing

    def to_json(self):
        data = super().to_json()
        data["text"] = self.text
        return data

    def __hash__(self):
        return id(self)


@dataclass
class Node(ShapeElement):
    ports: Dict[str, Port] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)

    _edges: set = field(init=False, repr=False, default_factory=set)  # could be a set?

    def __post_init__(self, **kwargs):
        for key, port in self.ports.items():
            port_parent(self, port)

    def __getattr__(self, key):
        if key in self.ports:
            return self.ports.get(key)
        shape_ports = getattr(self.shape, "ports", {})
        if key in shape_ports:
            return self.add_port(key, Port())
        # TODO decide on bad magic to create a port if it doesn't exist?
        raise AttributeError

    def to_json(self):
        data = super().to_json()
        shape_ports = {p["id"].split(".")[-1]: p for p in data.get("ports", [])}
        ports = []

        for key, port in shape_ports.items():
            if key in self.ports:
                port = merge(self.ports[key].to_json(), port)
            ports.append(port)
        data["ports"] = ports
        return strip_none(data)

    def add_child(self, child: "Node") -> "Node":
        self.children.append(child)
        return child

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
        self._edges.add(edge)
        return edge

    def __setattr__(self, key, value):
        if isinstance(value, Port):
            self.add_port(key, value)
        else:
            super().__setattr__(key, value)

    def add_port(self, key, port: Port) -> Port:
        self.ports[key] = port_parent(self, port)
        return port

    def __hash__(self):
        return id(self)


def port_parent(node: Node, port: Port) -> Port:
    assert (
        port._parent is None or port._parent is node
    ), "Incoming port owned by different node"
    port._parent = node
    return port
