# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import random

import networkx as nx
import pytest

from ipyelk.elements import Edge, HierarchicalIndex, Node, Port, index, iter_edges
from ipyelk.loaders import NXLoader
from ipyelk.loaders.nx.nxutils import get_endpoint, tree_lca


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


@pytest.mark.parametrize("port_key", ["n", "m", "n.c", "m.p"])
def test_get_endpoint_makes_a_port_for_a_global_id_of_anything_else(port_key):
    """Only the endpoint's own port is found by global id; any other key is a key."""
    node = Node(id="n")
    node.add_child(Node(id="n.c"))
    other = Node(id="m")
    other_port = other.add_port(Port(id="m.p"))
    el_map = HierarchicalIndex.from_els(node, other)
    port = get_endpoint(el_map, "n", port_key=port_key)
    assert isinstance(port, Port)
    assert len(node.ports) == 1
    assert node.ports[0] is port
    assert port.properties.key == port_key
    assert len(other.ports) == 1
    assert other.ports[0] is other_port


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


def random_tree(seed: int, n_nodes: int) -> tuple[random.Random, nx.DiGraph]:
    """A random tree rooted at ``n0``, as a networkx hierarchy."""
    rng = random.Random(seed)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    tree: nx.DiGraph = nx.DiGraph()
    tree.add_node("n0")
    for i in range(1, n_nodes):
        tree.add_edge(f"n{rng.randrange(i)}", f"n{i}")
    return rng, tree


@pytest.mark.parametrize("seed", range(4))
def test_tree_lca_matches_networkx(seed):
    """The parent walk gives the ancestor that ``nx.lowest_common_ancestor`` gives."""
    rng, tree = random_tree(seed, 200)
    nodes = list(tree)
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(300)]
    pairs += [(node, node) for node in nodes[:10]]
    pairs += list(tree.edges)[:10]  # a parent and its child
    for u, v in pairs:
        assert tree_lca(tree, u, v) == nx.lowest_common_ancestor(tree, u, v)


@pytest.mark.parametrize("seed", range(4))
def test_nx_loader_edge_owners_match_networkx(seed):
    """Each edge goes to the owner that the loader gave it with networkx."""
    rng, hierarchy = random_tree(seed, 120)
    nodes = list(hierarchy)
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(nodes)
    for i in range(200):
        u, v = rng.choice(nodes), rng.choice(nodes)
        if u == v == "n0":
            continue  # a self loop on the root has no parent to own it
        ports = {"sourcePort": "out"} if rng.random() < 0.3 else {}
        graph.add_edge(u, v, id=f"e{i}", **ports)

    expected = {}
    for u, v, data in graph.edges(data=True):
        if u == v:
            # self loops are owned by their parent
            owner = next(iter(hierarchy.pred[u]))
        else:
            owner = nx.lowest_common_ancestor(hierarchy, u, v)
        expected[data["id"]] = owner

    mark = NXLoader().load(graph=graph, hierarchy=hierarchy)
    try:
        owners = {edge.id: owner.id for owner, edge in iter_edges(mark.value)}
    finally:
        mark.close()
    assert owners == expected
