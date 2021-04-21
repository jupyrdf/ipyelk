# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ipyelk.elements import MarkFactory, Node


def test_simple_factory():
    """Have factory generate graphs from only a single node"""
    n1 = Node()

    factory = MarkFactory()
    g, tree = factory(n1)
    assert len(g) == 1, "Expecting only one nodes"
    assert len(g.edges) == 0, "Expect no edges"
    assert len(tree) == 0, "Expecting no hierarchy"
    assert len(tree.edges) == 0, "Expecting no hierarchy"


def test_simple_flat():
    """Have factory generate graphs from two connected nodes"""
    n1 = Node()
    n2 = Node()
    n1.add_edge(n1, n2)

    factory = MarkFactory()
    g, tree = factory(n1, n2)
    assert len(g) == 2, "Expecting only two nodes"
    assert len(g.edges) == 1, "Expect only one edge"
    assert len(tree) == 0, "Expecting no hierarchy"
    assert len(tree.edges) == 0, "Expecting no hierarchy"


def test_simple_hierarchy():
    """Have factory generate graphs from connected parent child"""
    n1 = Node()
    n2 = Node()
    n1.add_edge(n1, n2)
    n1.add_child(n2, "x")

    factory = MarkFactory()
    g, tree = factory(n1)
    assert len(g) == 2, "Expecting only two nodes"
    assert len(g.edges) == 1, "Expect only one edge"
    assert len(tree) == 2, "Expecting two nodes in hierarchy"
    assert len(tree.edges) == 1, "Expect only one edge"
