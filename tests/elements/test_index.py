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
    exclude_layout,
    shapes,
)
from ipyelk.elements.elements import ShapeElement
from ipyelk.elements.index import (
    ElementIndex,
    IDReport,
    VisIndex,
    iter_edges,
    iter_elements,
    iter_labels,
    iter_visible,
)
from ipyelk.elements.serialization import to_json
from ipyelk.exceptions import NotFoundError, NotUniqueError

#: the Registry tests pin the deprecated tier: it warns and keeps working
REGISTRY_COMPAT = pytest.mark.filterwarnings(
    "ignore:ipyelk.elements.Registry is deprecated:DeprecationWarning"
)


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


def test_element_index_keys_an_idless_element_by_its_wire_id():
    root = Node(children=[Node(children=[Node()])])
    index = ElementIndex.from_els(root)
    leaf = root.children[0].children[0]
    assert index.elements[leaf.wire_id()] is leaf
    assert leaf.id is None, "indexing alone does not assign ids"
    assert root.model_dump()["children"][0]["children"][0]["id"] == leaf.wire_id()


@REGISTRY_COMPAT
def test_element_index_keeps_registry_generated_ids():
    node = Node()
    with Registry():
        index = ElementIndex.from_els(node)
        node_id = node.get_id()
        assert node_id is not None
    assert len(index.elements) == 1
    assert index.elements[node_id] is node


@REGISTRY_COMPAT
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
    with exclude_layout:
        back = convert_elkjson(json.loads(json.dumps(to_json(root, None))))
    for el in iter_elements(back):
        if isinstance(el, ShapeElement):
            el.width, el.height = width, height
    return ElementIndex.from_els(back)


def layout_input(el: ShapeElement) -> tuple:
    """The size ``el`` sends to a layout (``VisibilityPipe`` projects under
    ``exclude_layout``).
    """
    with exclude_layout:
        data = to_json(el, None)
    return data.get("width"), data.get("height")


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
        return layout_input(child)

    assert (child.width, child.height) == (80, 60)
    assert shape.radius == 6
    assert size() == (12, 12)
    # any other serialization, such as the view's, carries the laid-out size
    plain = to_json(child, None)
    assert (plain["width"], plain["height"]) == (80, 60)
    shape.radius = 20
    assert size() == (40, 40)
    # a size set on the node wins over the shape, as before the first layout,
    # and the next layout (which echoes it) does not demote it
    child.width = 100
    assert size() == (100, 40)
    index.update(laid_out(root, 100, 90))
    assert (child.width, child.height) == (100, 90)
    assert size() == (100, 40)


def test_update_keeps_a_size_the_user_set():
    """ELK echoes a leaf's size, so a user-set size must survive the echo (the
    text sizer round trip echoes every node before ELK even sees it).
    """
    shape = shapes.Circle(radius=6)
    child = Node(id="c", width=100, height=50, properties=NodeProperties(shape=shape))
    root = Node(id="root", children=[child])
    index = ElementIndex.from_els(root)

    def size():
        return layout_input(child)

    assert size() == (100, 50)
    index.update(laid_out(root, 100, 50))
    assert size() == (100, 50)
    # the element holds what the browser returned (#194: a visible port takes
    # its layout), the user's size stays the input
    index.update(laid_out(root, 100, 45))
    assert (child.width, child.height) == (100, 45)
    assert size() == (100, 50)
    # ``None`` drops the user's size: the shape is the input again
    child.height = None
    index.update(laid_out(root, 100, 60))
    assert (child.width, child.height) == (100, 60)
    assert size() == (100, 12)
    # assigning the laid-out size pins it
    child.height = child.height
    index.update(laid_out(root, 100, 70))
    assert (child.width, child.height) == (100, 70)
    assert size() == (100, 60)


def test_a_label_shape_width_wins_over_the_measured_width():
    """The frontend measures a label unless its shape sets both ``width`` and
    ``height``; a dimension the shape sets is still the input to the layout.
    """
    label = Label(
        id="l",
        text="Point",
        properties=LabelProperties(shape=shapes.LabelShape(width=100)),
    )
    root = Node(id="root", labels=[label])
    index = ElementIndex.from_els(root)

    index.update(laid_out(root, 57, 17))

    assert (label.width, label.height) == (57, 17)
    assert layout_input(label) == (100, 17)


def test_update_keeps_properties_edited_while_a_layout_was_in_flight():
    """``properties`` never change in the browser, so they are not copied back."""
    root, child = shaped_node(shapes.Circle(radius=6))
    index = ElementIndex.from_els(root)
    wire = laid_out(root)

    properties = child.properties
    child.properties.cssClasses = "new"
    child.properties.hidden = True
    index.update(wire)

    assert child.properties is properties
    assert child.properties.cssClasses == "new"
    assert child.properties.hidden is True
    assert child.width == 80


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
        assert layout_input(node) == (80, 70)
    assert layout_input(sized) == (30, 70)


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


def test_element_index_membership_is_by_id():
    node = Node(id="n")
    index = ElementIndex.from_els(node)
    assert "n" in index
    assert "elements" not in index
    assert "missing" not in index
    assert 1 in ElementIndex.from_els(Node(id="1"))


def test_iter_labels_yields_every_label_in_tree_order():
    child = Node(id="c", labels=[Label(text="x"), Label(text="y")])
    root = Node(
        id="n",
        labels=[Label(text="a"), Label(text="b"), Label(text="c")],
        children=[child],
    )
    pairs = [(el.id, label.text) for el, label in iter_labels(root)]
    assert pairs == [("n", "a"), ("n", "b"), ("n", "c"), ("c", "x"), ("c", "y")]


def test_root_without_a_parentless_node_is_not_found():
    root = Node(id="root", children=[Node(id="child")])
    index = ElementIndex.from_els(root)
    index.elements.pop("root")  # leaves only `child`, whose parent is `root`
    with pytest.raises(NotFoundError, match="no root"):
        index.root()


def test_root_of_several_parentless_nodes_is_not_unique():
    index = ElementIndex.from_els(Node(id="a"), Node(id="b"))
    with pytest.raises(NotUniqueError, match="2 roots"):
        index.root()


@pytest.mark.parametrize("deep", [False, True])
def test_assigning_a_copied_size_does_not_change_the_original_input(deep):
    _, node = shaped_node(shapes.Circle(radius=6))
    node.set_laid_out(80, 70)
    copied = node.model_copy(deep=deep)

    copied.width = 100

    assert layout_input(copied) == (100, 12)
    assert layout_input(node) == (12, 12)
    node.height = 50
    assert layout_input(node) == (12, 50)
    assert layout_input(copied) == (100, 12)


@pytest.mark.parametrize("deep", [False, True])
@pytest.mark.parametrize("update", [{"width": 100}, {"width": None}, {"height": 50}])
def test_model_copy_size_update_becomes_the_copys_input(deep, update):
    _, node = shaped_node(shapes.Circle(radius=6))
    node.width = 30
    node.set_laid_out(80, 70)

    copied = node.model_copy(update=update, deep=deep)

    expected = {"width": 30, "height": 12} | update
    expected = {
        key: (12 if value is None else value) for key, value in expected.items()
    }
    assert layout_input(copied) == (expected["width"], expected["height"])
    assert layout_input(node) == (30, 12)
    assert (node.width, node.height) == (80, 70)
