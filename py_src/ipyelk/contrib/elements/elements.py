# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Tuple, Union

from ...diagram.elk_model import strip_none
from ...diagram.symbol import Symbol
from ...transform import merge
from .registry import Registry


@dataclass
class Element:
    shape: Optional[Symbol] = None
    labels: List["Label"] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)
    layoutOptions: Dict = field(default_factory=dict)

    def to_json(self):
        if isinstance(self.shape, Symbol):
            data = self.shape.to_json(id=Registry.get_id(self))
        else:
            data = {"id": Registry.get_id(self)}
        labels = data["labels"] = data.get("labels", [])
        labels.extend([l.to_json() for l in self.labels])
        data["properties"] = merge(self.properties, data.get("properties", {}))
        data["layoutOptions"] = merge(self.layoutOptions, data.get("layoutOptions", {}))

        return strip_none(data)

    def __hash__(self):
        return id(self)


@dataclass
class Port(Element):
    _parent: Optional["Node"] = None

    def to_json(self):
        data = super().to_json()
        parent_id = Registry.get_id(self._parent)
        self_id = Registry.get_id(self)
        data["id"] = ".".join([parent_id, self_id])
        return data

    def __hash__(self):
        return id(self)


@dataclass
class Label(Element):
    text: str = ""

    def to_json(self):
        data = super().to_json()
        data["text"] = self.text
        return data

    def __hash__(self):
        return id(self)


@dataclass
class Node(Element):
    ports: Dict[str, Port] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)

    def __post_init__(self, **kwargs):
        for key, port in self.ports.items():
            port_parent(self, port)

    def __getattr__(self, key):

        if key in self.ports:
            return self.ports.get(key)
        # TODO decide on bad magic to create a port if it doesn't exist?
        raise AttributeError

    def to_json(self):
        data = super().to_json()
        ports = data["ports"] = data.get("ports", [])
        ports.extend([p.to_json() for p in self.ports.values()])
        return strip_none(data)

    def add_child(self, child: "Node"):
        self.children.append(child)

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
