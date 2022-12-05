# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from ipyelk.elements import Edge, HierarchicalIndex, Label, Node, Port, Registry


def test_self_edge_lca():
    """The self edge from one port to another port should be owned by the root node."""
    node = Node(labels=[Label(text="Node")])
    port1 = Port(
        labels=[Label(text="1")],
        width=10,
        height=10,
    )

    port2 = Port(
        labels=[Label(text="2")],
        width=10,
        height=10,
    )
    node.add_port(port1)
    node.add_port(port2)

    node.add_edge(source=port1, target=port2)
    root = Node(children=[node])

    context = Registry()
    with context:
        index = HierarchicalIndex.from_els(root)
        edge_report, id_report = index.get_reports()

    assert len(edge_report.lca_mismatch) == 1
    for edge, (current_owner, expected_owner) in edge_report.lca_mismatch.items():
        assert isinstance(edge, Edge)
        assert current_owner is node, "Root should be the new owner of the self edge"
        assert expected_owner is root
