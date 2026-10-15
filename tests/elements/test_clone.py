# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Node.clone(prefix)`` copies a fragment with fresh, deterministic ids (#160)."""

from ipywidgets import IntSlider

from ipyelk.elements import (
    Document,
    ElementIndex,
    Label,
    Node,
    NodeProperties,
    Port,
    iter_elements,
    shapes,
)


def fragment() -> tuple[Node, Node]:
    """A gate-like template: ports with ids, a labeled child, an inner edge,
    and an edge to a node outside the fragment.
    """
    outside = Node(id="outside")
    gate = Node(ports=[Port(id="in"), Port()], labels=[Label(text="gate")])
    inner = gate.add_child(Node(id="core"))
    gate.add_edge(gate.ports[0], inner).id = "wire"
    gate.add_edge(inner, outside).id = "out"
    return gate, outside


def test_every_id_of_the_copy_is_prefixed_and_set():
    gate, _ = fragment()
    copy = gate.clone("g1")
    pairs = list(zip(iter_elements(gate), iter_elements(copy), strict=True))
    for original, cloned in pairs:
        assert cloned is not original
        assert cloned.id == f"g1.{original.wire_id()}"
    assert copy.ports[0].id == "g1.in"
    assert copy.children[0].id == "g1.core"
    assert copy.ports[1].id.startswith(f"{copy.id}."), "a port id starts with its node"


def test_the_same_fragment_and_prefix_give_the_same_ids():
    gate, _ = fragment()
    first = [el.id for el in iter_elements(gate.clone("g1"))]
    again = [el.id for el in iter_elements(gate.clone("g1"))]
    other = [el.id for el in iter_elements(gate.clone("g2"))]
    assert first == again
    assert not set(first) & set(other)


def test_parents_and_edges_connect_the_copies():
    gate, outside = fragment()
    copy = gate.clone("g1")
    assert copy.get_parent() is None
    assert all(port.get_parent() is copy for port in copy.ports)
    assert copy.children[0].get_parent() is copy
    wire, out = copy.edges
    assert wire.source is copy.ports[0]
    assert wire.target is copy.children[0]
    assert out.source is copy.children[0]
    assert out.target is outside, "an edge to the outside keeps its endpoint"
    assert gate.edges[0].source is gate.ports[0], "the template is unchanged"


def test_copies_own_their_properties_and_share_widgets_and_metadata():
    slider = IntSlider()
    gate = Node(properties=NodeProperties(shape=shapes.Widget(widget=slider)))
    copy = gate.clone("g1")
    assert copy.properties is not gate.properties
    assert copy.properties.shape.widget is slider
    assert copy.metadata is gate.metadata
    copy.add_class("on")
    assert "on" not in gate.properties.cssClasses
    slider.close()


def test_two_copies_index_without_duplicate_ids():
    gate, outside = fragment()
    root = Node(id="root", children=[outside])
    for prefix in ("g1", "g2"):
        root.add_child(gate.clone(prefix))
    Document(root)
    report = ElementIndex.from_els(root).check_ids()
    assert not report.duplicated
    assert not report.null_ids
