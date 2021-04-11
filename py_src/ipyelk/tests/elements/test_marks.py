# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ipyelk.elements import MarkFactory, Node, Port, Edge


def test_simple_flat():
    n1 = Node()
    n2 = Node()
    n1.add_edge(n1, n2)

    factory = MarkFactory(n1)
    g, tree = factory()
    assert len(g) == 2, "Expecting only two nodes"
    assert len(g.edges) == 1, "Expect only one edge"
    assert len(tree) == 0, "Expecting no hierarchy"
    assert len(tree.edges) == 0, "Expecting no hierarchy"

def test_simple_hierarchy():
    n1 = Node()
    n2 = Node()
    n1.add_edge(n1, n2)
    n1.add_child(n2, "x")

    factory = MarkFactory(n1)
    g, tree = factory()
    assert len(g) == 2, "Expecting only two nodes"
    assert len(g.edges) == 1, "Expect only one edge"
    assert len(tree) == 2, "Expecting two nodes in hierarchy"
    assert len(tree.edges) == 1, "Expect only one edge"
