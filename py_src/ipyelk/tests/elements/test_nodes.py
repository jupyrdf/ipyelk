# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ipyelk.diagram.symbol import symbols
from ipyelk.elements import Edge, Label, Node, Port


def test_node_instances():
    n1 = Node()
    n1.to_json()


def test_add_port():
    key = "port"
    n = Node()
    p = n.add_port(Port(), key)
    assert p.parent is n, "Expect port parent to be the node"
    assert n.ports[key] is p, "Expect node port dict to return same port"


def test_edge_node_instances():
    n1 = Node()
    n2 = Node()
    e = Edge(
        source=n1,
        target=n2,
    )
    assert e.source is n1, "Edge source instance changed"
    assert e.target is n2, "Edge target instance changed"


def test_node_label_instance():
    label = Label()
    n = Node(labels=[label])
    assert n.labels[0] is label, "Expect node label instance to match"


def test_edge_port_instances():
    n1 = Node()
    x = n1.add_port(Port(), "x")
    n2 = Node()
    e = Edge(
        source=x,
        target=n2,
    )
    assert e.source is x, "Edge source instance changed"
    assert e.target is n2, "Edge target instance changed"


def test_node_shape():
    shape = symbols.Ellipse()
    n = Node(shape=shape)
    data = n.to_json()
    assert data["properties"]["shape"].get("type") == shape.type
