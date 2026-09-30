# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The visible projection ``VisibilityPipe`` sends to ELK (jupyrdf/ipyelk#169).

A hidden element's incident edges are re-routed to a slack port on its nearest
visible *ancestor*.  When that ancestor is the root there is no node to carry
the port (ELK's root graph cannot have ports), so the edge is dropped from the
projection; the kernel index keeps it and it returns when the element is shown.
"""

import json

from ipyelk.elements import (
    Node,
    NodeProperties,
    VisIndex,
    convert_elkjson,
    exclude_hidden,
    exclude_layout,
)
from ipyelk.elements.serialization import to_json
from ipyelk.pipes import MarkElementWidget

SLACK_EDGE = "slack-edge"


def project(root: Node) -> Node:
    """What ``VisibilityPipe.run`` does, without the widgets."""
    vis_index = VisIndex.from_els(root)
    vis_index.clear_slack(root)
    with exclude_hidden, exclude_layout:
        data = root.model_dump()
    return convert_elkjson(data, vis_index)


def root_with_hidden_first_child():
    """``root[a(hidden), b, c]`` with ``a->b`` and ``b->c``."""
    root = Node(id="root")
    a = root.add_child(Node(id="a", properties=NodeProperties(hidden=True)))
    b = root.add_child(Node(id="b"))
    c = root.add_child(Node(id="c"))
    root.add_edge(a, b).id = "e_ab"
    root.add_edge(b, c).id = "e_bc"
    return root


def test_hidden_compound_child_gets_slack_port_on_compound():
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    compound.add_child(Node(id="x"))
    y = compound.add_child(Node(id="y", properties=NodeProperties(hidden=True)))
    compound.add_child(Node(id="w"))
    z = root.add_child(Node(id="z"))
    root.add_edge(z, y).id = "e_zy"

    visible = project(root)

    (edge,) = visible.edges
    assert edge.id == "e_zy"
    assert SLACK_EDGE in edge.properties.cssClasses.split()
    port = edge.target
    assert port.id == "y"
    projected = {node.id: node for node in visible.children[0].children}
    assert projected["x"].ports == []
    assert projected["w"].ports == []
    assert visible.children[0].ports == [port]
    assert port.get_parent() is visible.children[0]
    assert visible.ports == []


def test_hidden_root_level_node_drops_its_edges():
    root = root_with_hidden_first_child()

    visible = project(root)

    assert visible.ports == []
    assert [child.id for child in visible.children] == ["b", "c"]
    assert [edge.id for edge in visible.edges] == ["e_bc"]
    wire = to_json(visible, None)
    assert [edge["id"] for edge in wire["edges"]] == ["e_bc"]
    assert SLACK_EDGE not in json.dumps(wire)
    assert wire.get("ports", []) == []


def test_dropped_edge_survives_roundtrip_and_reveal():
    root = root_with_hidden_first_child()
    a = root.children[0]
    e_ab, e_bc = root.edges
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)

    visible = project(root)
    wire = json.loads(json.dumps(to_json(visible, None)))
    assert [edge["id"] for edge in wire["edges"]] == ["e_bc"]

    # the browser hands the projection back; the kernel folds it into the index
    widget.value = convert_elkjson(wire)
    widget.persist()
    assert widget.index.elements["e_ab"] is e_ab
    assert widget.index.elements["e_bc"] is e_bc
    assert widget.index.elements["a"] is a
    assert e_ab.source is a
    assert widget.index.root is root

    a.properties.hidden = False
    revealed = project(root)
    assert [edge.id for edge in revealed.edges] == ["e_ab", "e_bc"]
    assert revealed.ports == []
    assert [child.id for child in revealed.children] == ["a", "b", "c"]
    for edge in revealed.edges:
        assert SLACK_EDGE not in edge.properties.cssClasses.split()
    assert revealed.edges[0].source.id == "a"
    assert [node.ports for node in revealed.children] == [[], [], []]
    widget.close()
