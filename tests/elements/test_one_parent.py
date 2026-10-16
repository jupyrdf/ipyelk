# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""An element under a second parent raises when it is attached (#160 defect 5)."""

import asyncio

import pytest

from ipyelk.elements import Compartment, Edge, Label, Node, Port, shapes
from ipyelk.pipes import MarkElementWidget, ValidationPipe


def test_a_label_under_a_second_parent_raises_at_construction():
    label = Label(id="L", text="shared")
    a = Node(id="A", labels=[label])
    with pytest.raises(ValueError, match="Label 'L' is already under Node 'A'") as info:
        Node(id="B", labels=[label])
    assert "Node 'B'" in str(info.value)
    assert a.labels == [label]


def test_a_label_under_a_second_parent_raises_at_assignment():
    label = Label(id="L")
    a = Node(id="A", labels=[label])
    edge = Edge(id="E", source=a, target=Node(id="T"))
    with pytest.raises(ValueError, match="Label 'L' is already under Node 'A'"):
        edge.labels = [label]
    parent = Label(id="P")
    with pytest.raises(ValueError, match="cannot also be under Label 'P'"):
        parent.labels = [label]


def test_the_message_tells_a_copy_from_its_original():
    original = Node(id="m", labels=[Label(id="L")])
    copy = original.model_copy()
    with pytest.raises(ValueError, match="cannot also be under another Node") as info:
        copy.labels = list(copy.labels)
    assert "under another Node 'm'. A shallow model_copy()" in str(info.value)


def test_the_message_names_an_element_without_an_id_without_minting_one():
    label = Label(text="shared")
    a = Node(labels=[label])
    unnamed = r"Label without an id \(text 'shared'\) is already under Node without"
    with pytest.raises(ValueError, match=unnamed) as info:
        Node(id="B", labels=[label])
    message = str(info.value)
    assert "so it cannot also be under Node 'B'." in message
    assert label._wire_id is None, "naming the label did not mint a wire id"
    assert a._wire_id is None


def test_a_detached_or_copied_label_can_be_attached_again():
    label = Label(id="L")
    a = Node(id="A", labels=[label])
    Node(id="B", labels=[label.model_copy()])
    a.labels = []
    b = Node(id="B2", labels=[label])
    assert b.labels[0] is label


def test_a_child_or_port_under_a_second_parent_raises():
    child = Node(id="c")
    port = Port(id="p")
    Node(id="A", children=[child], ports=[port])
    other = Node(id="B")
    with pytest.raises(ValueError, match="Node 'c' is already under Node 'A'"):
        other.add_child(child)
    with pytest.raises(ValueError, match="Port 'p' is already under Node 'A'"):
        other.add_port(port)


def test_a_child_moved_with_remove_child_attaches_again():
    child = Node(id="c")
    a = Node(id="A", children=[child])
    a.remove_child(child)
    assert Node(id="B").add_child(child).get_parent().id == "B"


def test_a_child_or_port_detached_by_assignment_attaches_again():
    """The old parent no longer lists them, so the new parent may take them."""
    child = Node(id="c")
    port = Port(id="p")
    a = Node(id="A", children=[child], ports=[port])
    a.children = []
    a.ports = []
    b = Node(id="B")
    assert b.add_child(child).get_parent() is b
    assert b.add_port(port).get_parent() is b


def test_a_compartment_gives_each_line_its_own_bullet():
    compartment = Compartment(bullet_shape=shapes.Icon(use="dot")).make_labels(
        headings=["parts"], content=["wheel", "tire"]
    )
    _, wheel, tire = compartment.labels
    (wheel_bullet,) = wheel.labels
    (tire_bullet,) = tire.labels
    assert wheel_bullet is not tire_bullet
    assert wheel_bullet.properties.shape.use == "dot"

    root = Node(id="root", children=[compartment])
    widget = MarkElementWidget(value=root)
    pipe = ValidationPipe(inlet=widget)
    asyncio.run(pipe.run())
    assert not pipe.id_report.duplicated
    assert wheel_bullet.id != tire_bullet.id
    pipe.close()
    widget.close()
