# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The visible projection ``VisibilityPipe`` sends to ELK (jupyrdf/ipyelk#169).

A hidden element's incident edges are re-routed to a slack port on its nearest
visible *ancestor*.  When that ancestor is the root there is no node to carry
the port (ELK's root graph cannot have ports), so the edge is dropped from the
projection; the kernel index keeps it and it returns when the element is shown.
"""

import json

import pytest

from ipyelk.elements import (
    Node,
    NodeProperties,
    Port,
    PortProperties,
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


def test_hidden_port_keeps_its_properties_after_a_slack_roundtrip():
    root = Node(id="root")
    source = root.add_child(Node(id="source"))
    hidden_port = source.add_port(
        Port(id="source.hidden", properties=PortProperties(hidden=True))
    )
    target = root.add_child(Node(id="target"))
    root.add_edge(hidden_port, target).id = "edge"
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)

    visible = project(root)
    slack_port = visible.children[0].ports[0]
    assert "slack-port" in slack_port.properties.cssClasses.split()

    widget.value = visible
    widget.persist()

    assert hidden_port.properties.hidden is True
    assert not hidden_port.properties.cssClasses
    widget.close()


PORT_GEOMETRY = {
    "x": 1.0,
    "y": 2.0,
    "width": 12.0,
    "height": 8.0,
    "layoutOptions": {"org.eclipse.elk.port.side": "WEST"},
}


def browser(widget: MarkElementWidget, root: Node, edit=None, vis_index=None) -> dict:
    """Project ``root``, send it through JSON, and merge it back like the browser."""
    vis_index = vis_index or VisIndex.from_els(root)
    vis_index.clear_slack(root)
    with exclude_hidden, exclude_layout:
        projected = convert_elkjson(root.model_dump(), vis_index)
    wire = json.loads(json.dumps(to_json(projected, None)))
    if edit is not None:
        edit(wire)
    widget.value = convert_elkjson(wire)
    widget.persist()
    return wire


def geometry(port: Port) -> dict:
    return {key: getattr(port, key) for key in PORT_GEOMETRY}


def nested_port(hide_port: bool):
    """``root > g1 > g2 > n`` with port ``n.p`` and an edge ``n.p -> other``.

    Either the port or ``n`` is hidden, so ``n.p`` projects as a slack port onto
    ``n`` or ``g2``.
    """
    root = Node(id="root")
    g2 = root.add_child(Node(id="g1")).add_child(Node(id="g2"))
    node = g2.add_child(Node(id="n", properties=NodeProperties(hidden=not hide_port)))
    port = node.add_port(
        Port(id="n.p", properties=PortProperties(hidden=hide_port), **PORT_GEOMETRY)
    )
    root.add_edge(port, root.add_child(Node(id="other"))).id = "edge"
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    return widget, root, port, port if hide_port else node


@pytest.mark.parametrize("hide_port", [True, False], ids=["hidden", "on-hidden-node"])
def test_projected_port_keeps_its_geometry(hide_port):
    widget, root, port, hidden = nested_port(hide_port)

    for _ in range(3):
        wire = browser(widget, root)
        assert "slack-port" in json.dumps(wire)
        assert geometry(port) == PORT_GEOMETRY
        assert widget.index.elements["n.p"] is port
        assert not port.properties.cssClasses

    hidden.properties.hidden = False
    wire = browser(widget, root)
    assert "slack-port" not in json.dumps(wire)
    assert geometry(port) == PORT_GEOMETRY
    widget.close()


def test_hidden_port_ignores_a_custom_slack_style():
    widget, root, port, _ = nested_port(hide_port=True)
    vis_index = VisIndex.from_els(root)
    vis_index.slack_port_style = {"my-slack"}

    wire = browser(widget, root, vis_index=vis_index)

    assert "my-slack" in json.dumps(wire)
    assert geometry(port) == PORT_GEOMETRY
    widget.close()


def test_port_revealed_during_a_layout_ignores_its_slack_port():
    """The layout that comes back was made while the port was still hidden."""
    widget, root, port, hidden = nested_port(hide_port=True)

    def reveal(wire):
        hidden.properties.hidden = False

    browser(widget, root, reveal)

    assert geometry(port) == PORT_GEOMETRY
    widget.close()


def test_visible_port_takes_the_layout():
    root = Node(id="root")
    a = root.add_child(Node(id="a"))
    port = a.add_port(Port(id="a.p", **PORT_GEOMETRY))
    root.add_edge(port, root.add_child(Node(id="b"))).id = "edge"
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    laid_out = {
        "x": 3.0,
        "y": 4.0,
        "width": 9.0,
        "height": 7.0,
        "layoutOptions": {"org.eclipse.elk.port.side": "EAST"},
    }

    browser(widget, root, lambda wire: wire["children"][0]["ports"][0].update(laid_out))

    assert {key: getattr(port, key) for key in laid_out} == laid_out
    widget.close()


def test_moved_port_takes_the_layout():
    """A port moved to another node keeps its id and still takes its layout."""
    root = Node(id="root")
    a = root.add_child(Node(id="a"))
    b = root.add_child(Node(id="b"))
    port = a.add_port(Port(id="p"))
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    a.ports.remove(port.set_parent(None))
    b.add_port(port)

    browser(
        widget, root, lambda wire: wire["children"][1]["ports"][0].update(x=3.0, y=4.0)
    )

    assert (port.x, port.y) == (3.0, 4.0)
    assert widget.index.elements["p"] is port
    widget.close()
