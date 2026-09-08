# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from ipyelk.elements import Edge, Label, Node, Port, shapes


def test_node_instances():
    n1 = Node()
    n1.model_dump()


def test_add_child():
    key = "child"
    n = Node()
    p = n.add_child(Node(), key)
    assert p.get_parent() is n, "Expect port parent to be the node"
    assert n.get_child(key) is p, "Expect node port dict to return same port"
    n.model_dump()


def test_add_port():
    key = "port"
    n = Node()
    p = n.add_port(Port(), key)
    assert p.get_parent() is n, "Expect port parent to be the node"
    assert n.get_port(key) is p, "Expect node port dict to return same port"
    n.model_dump()


def test_edge_node_instances():
    n1 = Node()
    n2 = Node()
    e = Edge(
        source=n1,
        target=n2,
    )
    assert e.source is n1, "Edge source instance changed"
    assert e.target is n2, "Edge target instance changed"
    n1.model_dump()
    n2.model_dump()
    e.model_dump()


def test_node_label_instance():
    label = Label()
    n = Node(labels=[label])
    assert n.labels[0] is label, "Expect node label instance to match"
    label.model_dump()


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
    n1.model_dump()
    x.model_dump()
    n2.model_dump()
    e.model_dump()


def test_node_shape():
    shape = shapes.Ellipse()
    n = Node(properties={"shape": shape})
    data = n.model_dump()
    assert data["properties"]["shape"].get("type") == shape.type
