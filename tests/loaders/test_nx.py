# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import networkx as nx
import pytest

from ipyelk.elements import Edge, HierarchicalIndex, Node, Port, index
from ipyelk.loaders import NXLoader
from ipyelk.loaders.nx.nxutils import get_endpoint


def test_nx_port_ids_prefixed_by_node_id():
    graph = nx.MultiDiGraph()
    graph.add_edge("x", "y", sourcePort="out", targetPort="in")
    mark = NXLoader().load(graph=graph)
    try:
        ports = [el for el in index.iter_elements(mark.value) if isinstance(el, Port)]
        edges = [el for el in index.iter_elements(mark.value) if isinstance(el, Edge)]
        assert len(ports) == 2
        for port in ports:
            parent = port.get_parent()
            assert parent is not None
            assert port.id is not None
            assert port.id.startswith(f"{parent.id}.")
            assert port.get_id() == port.id
        assert len(edges) == 1
        edge = edges[0]
        assert edge.sources == [edge.source.id]
        assert edge.targets == [edge.target.id]
        assert {edge.source.get_parent().id, edge.target.get_parent().id} == {
            "x",
            "y",
        }
        # the loader's ids are the ones the index is keyed by
        mark.persist(rebuild_index=True)
        for port in ports:
            assert mark.index.elements.get(port.id) is port
    finally:
        mark.close()


def test_get_endpoint_finds_a_port_by_its_global_id():
    node = Node(id="n")
    port = node.add_port(Port(id="n.p"))
    el_map = HierarchicalIndex.from_els(node)
    assert get_endpoint(el_map, "n", port_key="n.p") is port
    assert len(node.ports) == 1
    assert node.ports[0] is port


def test_get_endpoint_rejects_another_nodes_port_id():
    node = Node(id="n")
    other = Node(id="m")
    other.add_port(Port(id="m.p"))
    el_map = HierarchicalIndex.from_els(node, other)
    with pytest.raises(ValueError, match="consistent with the edge"):
        get_endpoint(el_map, "n", port_key="m.p")
    assert node.ports == []


@pytest.mark.parametrize("port_key", ["n", "m", "n.c"])
def test_get_endpoint_makes_a_port_for_a_key_that_names_a_node(port_key):
    node = Node(id="n")
    node.add_child(Node(id="n.c"))
    other = Node(id="m")
    el_map = HierarchicalIndex.from_els(node, other)
    port = get_endpoint(el_map, "n", port_key=port_key)
    assert isinstance(port, Port)
    assert len(node.ports) == 1
    assert node.ports[0] is port
    assert port.properties.key == port_key


def test_nx_port_keys_may_match_node_ids():
    graph = nx.MultiDiGraph()
    graph.add_edge("in", "process", sourcePort="out", targetPort="in")
    graph.add_edge("process", "out", sourcePort="out", targetPort="in")
    mark = NXLoader().load(graph=graph)
    try:
        ports = [el for el in index.iter_elements(mark.value) if isinstance(el, Port)]
        found = sorted((port.get_parent().id, port.properties.key) for port in ports)
        assert found == [
            ("in", "out"),
            ("out", "in"),
            ("process", "in"),
            ("process", "out"),
        ]
    finally:
        mark.close()


def test_nx_edge_lands_on_an_existing_port_by_global_id():
    a = Node(id="a")
    out = a.add_port(Port(id="a.out"))
    b = Node(id="b")
    graph = nx.MultiDiGraph()
    graph.add_edge(a, b, sourcePort="a.out")
    mark = NXLoader().load(graph=graph)
    try:
        assert len(a.ports) == 1
        assert a.ports[0] is out
        edges = [el for el in index.iter_elements(mark.value) if isinstance(el, Edge)]
        assert len(edges) == 1
        assert edges[0].source is out
        assert edges[0].target is b
    finally:
        mark.close()
