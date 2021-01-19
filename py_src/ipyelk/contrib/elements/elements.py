# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Type, Union

from ...diagram.elk_model import strip_none
from ...diagram.symbol import Symbol
from ...transform import merge
from .registry import Registry


def id_hash(self):
    return hash(id(self))


def element(
    _cls=None,
    *,
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=False
):
    def wrap(cls):
        wrapped = dataclass(
            cls,
            init=init,
            repr=repr,
            eq=eq,
            order=order,
            unsafe_hash=unsafe_hash,
            frozen=frozen,
        )
        if getattr(wrapped, "__hash__", None) is None:
            wrapped.__hash__ = id_hash
        return wrapped

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called with parens.
        return wrap

    # We're called as @dataclass without parens.
    return wrap(_cls)


@element
class BaseElement:
    labels: List["Label"] = field(default_factory=list)
    properties: Dict = field(default_factory=dict)
    layoutOptions: Dict = field(default_factory=dict)

    _dom_classes: List[str] = field(init=False, repr=False, default_factory=list)
    _css_classes: ClassVar[List[str]] = []

    def __post_init__(self, *args, **kwargs):
        classes = self._css_classes or []
        for css_class in classes:
            self.add_class(css_class)

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


@element
class Edge(BaseElement):
    shape_end: Optional[str] = None  # TODO maybe should be a ConnectorDef object
    shape_start: Optional[str] = None

    source: Union["Node", "Port"] = None
    target: Union["Node", "Port"] = None

    def to_json(self):
        props = self.properties
        shape = props["shape"] = props.get("shape", {})
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
        u = self.source if isinstance(self.source, Node) else self.source._parent
        v = self.target if isinstance(self.target, Node) else self.target._parent
        return u, v


@element
class ShapeElement(BaseElement):
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


@element
class Port(ShapeElement):
    _parent: Optional["Node"] = field(init=False, repr=False, default=None)

    def to_json(self):
        data = super().to_json()
        parent_id = Registry.get_id(self._parent)
        self_id = Registry.get_id(self)
        data["id"] = ".".join([parent_id, self_id])
        data["properties"]["type"] = "port"
        return data


@element
class Label(ShapeElement):
    text: str = " "  # completely empty strings exclude label in node sizing

    def to_json(self):
        data = super().to_json()
        data["text"] = self.text
        return data


@element
class Node(ShapeElement):
    ports: Dict[str, Port] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)

    _edges: set = field(init=False, repr=False, default_factory=set)  # could be a set?
    _child_namespace: Dict[str, "Node"] = field(
        init=False, repr=False, default_factory=dict
    )

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(self, *args, **kwargs)
        for key, port in self.ports.items():
            port_parent(self, port)

    def __getattr__(self, key):
        if key in self._child_namespace:
            return self._child_namespace.get(key)
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

    def add_child(self, child: "Node", key: str = "") -> "Node":
        self.children.append(child)
        if key:
            self._child_namespace[key] = child
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
        self._edges.add(edge)
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
        port._parent is None or port._parent is node
    ), "Incoming port owned by different node"
    port._parent = node
    return port
