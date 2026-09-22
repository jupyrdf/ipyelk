# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The parent-walk lowest common ancestor must agree with ``networkx``.

``ElementIndex.check_edges`` used to build a ``nx.DiGraph`` of the whole
hierarchy and call ``nx.lowest_common_ancestor`` once per edge.  These tests pin
the replacement (``ElementIndex.depths`` plus ``ElementIndex.lca_by_parent``) to
that behaviour, networkx included.
"""

from __future__ import annotations

import random

import networkx as nx
import pytest

from ipyelk.elements import (
    Edge,
    ElementIndex,
    HierarchicalElement,
    Node,
    Port,
    Registry,
    iter_edges,
    iter_hierarchy,
)
from ipyelk.exceptions import NotFoundError


def nx_hierarchy(root: Node, *orphans: Node) -> nx.DiGraph:
    """The hierarchy graph ``check_edges`` used to build, orphans and all."""
    hierarchy: nx.DiGraph = nx.DiGraph()
    hierarchy.add_edges_from(iter_hierarchy(root, types=(HierarchicalElement,)))
    hierarchy.add_edges_from(
        iter_hierarchy(*orphans, root=root, types=(HierarchicalElement,))
    )
    return hierarchy


def nx_owner(hierarchy: nx.DiGraph, edge: Edge) -> Node:
    """The owner networkx would pick for ``edge`` (``nxutils.get_owner``)."""
    u, v = (
        end.get_parent() if isinstance(end, Port) else end
        for end in (edge.source, edge.target)
    )
    if u is v:
        # self loops are owned by their parent
        return u.get_parent()
    owner = nx.lowest_common_ancestor(hierarchy, u, v)
    assert isinstance(owner, Node)
    return owner


def assert_matches_networkx(root: Node, index: ElementIndex | None = None):
    """Every edge's reported owner is the one networkx's LCA would give."""
    if index is None:
        index = ElementIndex.from_els(root)
    report = index.check_edges()
    hierarchy = nx_hierarchy(root, *report.orphans)

    checked = 0
    for owner, edge in iter_edges(root, *report.orphans):
        expected = nx_owner(hierarchy, edge)
        if expected is owner:
            assert edge not in report.lca_mismatch, (
                f"{edge.get_id()} is already owned by {owner.get_id()}"
            )
        else:
            reported = report.lca_mismatch.get(edge)
            assert reported is not None, f"{edge.get_id()} should be reported"
            assert reported[0] is owner, (
                f"{edge.get_id()} should be reported as owned by {owner.get_id()}"
            )
            assert reported[1] is expected, (
                f"{edge.get_id()} should move from "
                f"{owner.get_id()} to {expected.get_id()}"
            )
        checked += 1
    return report, checked


def random_hierarchy(seed: int, n_nodes: int, n_edges: int) -> tuple[Node, int]:
    """A random tree with random edges hung off random (not always correct) owners."""
    rng = random.Random(seed)  # ruff: ignore[suspicious-non-cryptographic-random-usage]
    root = Node(id="root")
    nodes = [root]
    for i in range(n_nodes):
        parent = rng.choice(nodes)
        node = parent.add_child(Node(id=f"n{i}"))
        if rng.random() < 0.4:
            node.add_port(Port(id=f"n{i}.p0"))
            node.add_port(Port(id=f"n{i}.p1"))
        nodes.append(node)

    def endpoint(node: Node) -> HierarchicalElement:
        if node.ports and rng.random() < 0.5:
            return rng.choice(node.ports)
        return node

    edges = 0
    while edges < n_edges:
        source, target = rng.choice(nodes), rng.choice(nodes)
        if source is root or target is root:
            # a self loop on the root has no parent to be owned by
            continue
        # the owner is deliberately arbitrary: that is what check_edges fixes
        rng.choice(nodes).add_edge(endpoint(source), endpoint(target))
        edges += 1
    return root, edges


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_parent_walk_matches_networkx(seed):
    """Random hierarchies: same owner for every edge as ``nx.lowest_common_ancestor``."""
    root, n_edges = random_hierarchy(seed, n_nodes=120, n_edges=200)
    with Registry():
        report, checked = assert_matches_networkx(root)

    assert checked == n_edges, "every edge should have been compared"
    assert report.lca_mismatch, "a random hierarchy should need some re-owning"

    # re-owning every edge settles it: the second pass agrees with networkx that
    # there is nothing left to move
    for edge, (old_owner, new_owner) in report.lca_mismatch.items():
        old_owner.edges.remove(edge)
        new_owner.edges.append(edge)
    with Registry():
        settled, checked = assert_matches_networkx(root)
    assert checked == n_edges
    assert not settled.lca_mismatch


def test_self_loop_owned_by_parent():
    """A self loop -- node to itself, or between two ports of one node -- goes to
    the node's parent.
    """
    root = Node(id="root")
    group = root.add_child(Node(id="group"))
    node = group.add_child(Node(id="node"))
    port1 = node.add_port(Port(id="p1"))
    port2 = node.add_port(Port(id="p2"))

    to_self = node.add_edge(node, node)
    to_self.id = "to_self"
    between_ports = node.add_edge(port1, port2)
    between_ports.id = "between_ports"
    already_owned = group.add_edge(port1, port2)
    already_owned.id = "already_owned"

    with Registry():
        report, _ = assert_matches_networkx(root)

    assert report.lca_mismatch == {
        to_self: (node, group),
        between_ports: (node, group),
    }, "self loops belong to the parent, and only the misplaced ones are reported"


def test_port_endpoints_resolve_to_parents():
    """A port endpoint counts as its owning node, so the LCA is the same as for
    the nodes themselves.
    """
    root = Node(id="root")
    left = root.add_child(Node(id="left"))
    right = root.add_child(Node(id="right"))
    a = left.add_child(Node(id="a"))
    b = left.add_child(Node(id="b"))
    c = right.add_child(Node(id="c"))
    a_port = a.add_port(Port(id="a.p"))
    b_port = b.add_port(Port(id="b.p"))
    c_port = c.add_port(Port(id="c.p"))

    siblings = root.add_edge(a_port, b_port)
    siblings.id = "siblings"
    cousins = left.add_edge(a_port, c_port)
    cousins.id = "cousins"
    mixed = root.add_edge(a, b_port)
    mixed.id = "mixed"

    with Registry():
        report, _ = assert_matches_networkx(root)

    assert report.lca_mismatch == {
        siblings: (root, left),
        cousins: (left, root),
        mixed: (root, left),
    }


def test_orphan_adoption_unchanged():
    """An endpoint outside the hierarchy is reported by its topmost ancestor, and
    the ancestor lookup treats that ancestor as a child of the root.
    """
    root = Node(id="root")
    group = root.add_child(Node(id="group"))
    inside = group.add_child(Node(id="inside"))

    stray = Node(id="stray")
    stray_child = stray.add_child(Node(id="stray_child"))
    stray_other = stray.add_child(Node(id="stray_other"))

    crossing = root.add_edge(inside, stray_child)
    crossing.id = "crossing"
    within_orphan = root.add_edge(stray_child, stray_other)
    within_orphan.id = "within_orphan"

    with Registry():
        report, _ = assert_matches_networkx(root)

    assert report.orphans == {stray}, "the topmost ancestor is the orphan"
    assert report.lca_mismatch == {
        # the orphan hangs off the root, so an edge crossing into it stays put
        within_orphan: (root, stray),
    }


def test_self_loop_on_a_parentless_node_still_raises():
    """Pinned, not endorsed: a self loop on a node with no parent has no owner,
    and the networkx implementation failed on it too.
    """
    root = Node(id="root")
    root.add_child(Node(id="child"))
    root.add_edge(root, root).id = "loop"

    with Registry():
        index = ElementIndex.from_els(root)
        with pytest.raises(NotFoundError):
            index.check_edges()


def test_depths_counts_from_the_root_and_adopts_orphans():
    root = Node(id="root")
    group = root.add_child(Node(id="group"))
    leaf = group.add_child(Node(id="leaf"))
    orphan = Node(id="orphan")
    orphan_leaf = orphan.add_child(Node(id="orphan_leaf"))

    depths = ElementIndex.depths(root, orphan)

    assert depths[id(root)] == 0
    assert depths[id(group)] == 1
    assert depths[id(leaf)] == 2
    assert depths[id(orphan)] == 1, "orphans are adopted by the root"
    assert depths[id(orphan_leaf)] == 2
    assert len(depths) == 5, "only nodes are walked"

    assert ElementIndex.lca_by_parent(leaf, orphan_leaf, depths, root=root) is root
    assert ElementIndex.lca_by_parent(leaf, group, depths, root=root) is group
    assert ElementIndex.lca_by_parent(leaf, leaf, depths, root=root) is group
