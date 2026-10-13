# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import json

import pytest
from ipywidgets import HTML

from ipyelk.elements import (
    EdgeProperties,
    Label,
    LabelProperties,
    Node,
    NodeProperties,
    Port,
    PortProperties,
    Registry,
    convert_elkjson,
    shapes,
)
from ipyelk.elements.elements import ShapeElement
from ipyelk.elements.index import (
    ElementIndex,
    IDReport,
    VisIndex,
    iter_edges,
    iter_elements,
    iter_visible,
)
from ipyelk.elements.serialization import to_json


def test_id_report_message_interpolates_duplicated_ids():
    node = Node(id="dup")
    report = IDReport(duplicated={"dup": [node]})
    message = report.message()
    assert "dup" in message
    assert "{eid}" not in message


def test_id_report_message_interpolates_null_ids():
    node = Node()
    report = IDReport(null_ids=[node])
    message = report.message()
    assert "{el}" not in message
    assert str(node) in message


def test_element_index_rejects_unresolved_missing_id():
    root = Node(children=[Node(children=[Node()])])
    with pytest.raises(ValueError, match="without an id") as excinfo:
        ElementIndex.from_els(root)
    # the message names the element type, not the (recursive) element repr
    assert str(excinfo.value).startswith("Cannot index element without an id (Node)")
    assert "children" not in str(excinfo.value)


def test_element_index_keeps_registry_generated_ids():
    node = Node()
    with Registry():
        index = ElementIndex.from_els(node)
        node_id = node.get_id()
        assert node_id is not None
    assert len(index.elements) == 1
    assert index.elements[node_id] is node


def test_vis_index_keeps_registry_generated_ids():
    root = Node(children=[Node(properties=NodeProperties(hidden=True))])
    hidden = root.children[0]
    with Registry():
        index = VisIndex.from_els(root)
        hidden_id = hidden.get_id()
        root_id = root.get_id()
        assert hidden_id is not None
        assert root_id is not None
    assert hidden_id in index.hidden
    assert index.last_visible[hidden_id] == root_id


def _compound_with_hidden_middle_child():
    """``C[x, y(hidden), w]``: the hidden child sits between two visible ones."""
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    compound.add_child(Node(id="x"))
    compound.add_child(Node(id="y", properties=NodeProperties(hidden=True)))
    compound.add_child(Node(id="w"))
    return root, compound


def test_iter_visible_does_not_leak_hidden_to_siblings():
    root, compound = _compound_with_hidden_middle_child()
    x, y, w = compound.children
    visited = {el.id: (el, hidden, last) for el, hidden, last in iter_visible(root)}
    assert visited["y"] == (y, True, compound)
    # `w` follows the hidden sibling: not hidden, and its nearest visible element
    # is itself, not `x` (the preceding visible sibling)
    assert visited["w"] == (w, False, w)
    assert visited["x"] == (x, False, x)
    assert visited["C"] == (compound, False, compound)
    assert [el.id for el, hidden, _ in iter_visible(root) if hidden] == ["y"]


def test_vis_index_last_visible_is_the_parent():
    root, _compound = _compound_with_hidden_middle_child()
    index = VisIndex.from_els(root)
    assert index.last_visible["y"] == "C"
    assert "w" not in index.hidden
    assert "x" not in index.hidden
    assert set(index.hidden) == {"y"}


def test_iteration_follows_child_order():
    """Tree order decides which of two clashing derived ids is kept."""
    root = Node(id="root")
    children = [root.add_child(Node(id=f"c{i}")) for i in range(12)]
    for child in children:
        child.add_edge(child, child).id = f"e{child.id}"

    nodes = [el.id for el in iter_elements(root) if isinstance(el, Node)]
    assert nodes[1:] == [c.id for c in children]
    assert [owner.id for owner, _ in iter_edges(root)] == [c.id for c in children]


def laid_out(root: Node, width: float = 80.0, height: float = 80.0) -> ElementIndex:
    """What ``persist`` merges after a layout: the wire form of ``root`` parsed
    back, with a laid-out size on every node, port and label.
    """
    back = convert_elkjson(json.loads(json.dumps(to_json(root, None))))
    for el in iter_elements(back):
        if isinstance(el, ShapeElement):
            el.width, el.height = width, height
    return ElementIndex.from_els(back)


def shaped_node(shape: shapes.NodeShape) -> tuple[Node, Node]:
    child = Node(id="c", properties=NodeProperties(shape=shape))
    return Node(id="root", children=[child]), child


def typed(shape: shapes.NodeShape, **fields):
    """A test case: ``shape`` and the field values it must keep."""
    return pytest.param(shape, fields, id=type(shape).__name__)


@pytest.mark.parametrize(
    ("shape", "fields"),
    [
        typed(shapes.Circle(radius=6), radius=6),
        typed(shapes.Ellipse(rx=4, ry=3), rx=4, ry=3),
        typed(shapes.Path(use="M0,0L10,10Z"), use="M0,0L10,10Z"),
        typed(shapes.SVG(use="<circle r='5'/>"), use="<circle r='5'/>"),
        typed(shapes.Use(use="final_state"), use="final_state"),
        typed(shapes.Image(use="a.png"), use="a.png"),
        typed(shapes.ForeignObject(use="<b>x</b>"), use="<b>x</b>"),
        typed(shapes.HTML(use="<b>x</b>"), use="<b>x</b>"),
        typed(shapes.Comment(use=20), use="20"),
        typed(shapes.Diamond()),
        typed(shapes.Rect()),
        typed(shapes.NodeShape(width=30, height=20), width=30, height=20),
        typed(shapes.Widget(widget=HTML("x"), delay=100), delay=100),
    ],
)
def test_update_keeps_the_typed_node_shape(shape, fields):
    """A node keeps its own shape object through a layout round trip (#201)."""
    root, child = shaped_node(shape)
    index = ElementIndex.from_els(root)

    index.update(laid_out(root))

    assert child.properties.shape is shape
    assert type(child.properties.shape) is type(shape)
    for name, value in fields.items():
        assert getattr(shape, name) == value
    if isinstance(shape, shapes.Widget):
        assert shape.widget.model_id == shape.model_dump()["use"]
    assert (child.width, child.height) == (80, 80)


def test_update_keeps_label_port_and_edge_shapes():
    """``Icon``, ``PortShape`` and ``EdgeShape`` survive like node shapes (#201)."""
    icon = shapes.Icon(use="class", width=12, height=12)
    label = Label(
        id="l",
        text="Point",
        labels=[Label(id="l.i", text=" ", properties=LabelProperties(shape=icon))],
    )
    port_shape = shapes.PortShape(use="pin")
    edge_shape = shapes.EdgeShape(end="arrow")
    a = Node(id="a", labels=[label])
    port = a.add_port(Port(id="a.p", properties=PortProperties(shape=port_shape)))
    b = Node(id="b")
    root = Node(id="root", children=[a, b])
    edge = root.add_edge(port, b)
    edge.id = "e"
    edge.properties = EdgeProperties(shape=edge_shape)
    index = ElementIndex.from_els(root)

    index.update(laid_out(root))

    nested = label.labels[0].properties.shape
    assert nested is icon
    assert isinstance(nested, shapes.Icon)
    assert nested.use == "class"
    assert port.properties.shape is port_shape
    assert port.properties.shape.use == "pin"
    assert edge.properties.shape is edge_shape
    assert edge.properties.shape.end == "arrow"


def test_radius_set_after_a_round_trip_resizes_the_node():
    """The laid-out size is on the node, but the shape's size is still the input
    to the next layout, and ``radius`` can be set after a round trip (#201).
    """
    shape = shapes.Circle(radius=6)
    root, child = shaped_node(shape)
    index = ElementIndex.from_els(root)

    index.update(laid_out(root, 80, 60))

    def size():
        data = to_json(child, None)
        return data["width"], data["height"]

    assert (child.width, child.height) == (80, 60)
    assert shape.radius == 6
    assert size() == (12, 12)
    shape.radius = 20
    assert size() == (40, 40)
    # a size set on the node wins over the shape, as before the first layout
    child.width = 100
    assert size() == (100, 40)
    # the next layout's size is laid out again, the user's width is not
    index.update(laid_out(root, 100, 90))
    assert (child.width, child.height) == (100, 90)
    assert size() == (40, 40)


def test_update_keeps_the_laid_out_size_of_a_shape_without_one():
    """A shape with no size of its own, or no shape, re-sends the laid-out size."""
    plain = shapes.NodeShape()
    root = Node(
        id="root",
        children=[
            Node(id="plain", properties=NodeProperties(shape=plain)),
            Node(id="bare"),
            Node(id="sized", properties=NodeProperties(shape=shapes.Rect(width=30))),
        ],
    )
    plain_node, bare, sized = root.children
    index = ElementIndex.from_els(root)

    index.update(laid_out(root, 80, 70))

    assert plain_node.properties.shape is plain
    assert type(plain) is shapes.NodeShape
    for node in (plain_node, bare):
        assert (node.width, node.height) == (80, 70)
        data = to_json(node, None)
        assert (data["width"], data["height"]) == (80, 70)
    data = to_json(sized, None)
    assert (data["width"], data["height"]) == (30, 70)


def test_update_keeps_a_shape_replaced_between_layouts():
    """What the user set since the layout was sent wins over what comes back."""
    root, child = shaped_node(shapes.Circle(radius=6))
    index = ElementIndex.from_els(root)
    wire = laid_out(root)

    replacement = shapes.Diamond()
    child.properties.shape = replacement
    index.update(wire)
    assert child.properties.shape is replacement

    child.properties.shape = None
    index.update(laid_out(root))
    assert child.properties.shape is None
    assert not child.properties.cssClasses
