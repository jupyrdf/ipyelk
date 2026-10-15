# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The models agree with ``elkschema.json``, the ELK JSON schema of the frontend.

The TypeScript types of the frontend generate ``elkschema.json``.
These tests are the drift check of #131 and #153: every key the models can write
is in the schema, and a payload with every kind of element validates.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from ipywidgets import IntSlider
from pydantic import BaseModel, ValidationError

import ipyelk.contrib.library.block  # ruff: ignore[unused-import] (registers the subclasses)
from ipyelk.elements import (
    Compartment,
    Edge,
    EdgeProperties,
    Label,
    LabelProperties,
    Node,
    NodeProperties,
    Port,
    PortProperties,
    Record,
    VisIndex,
    convert_elkjson,
    exclude_hidden,
    exclude_layout,
    shapes,
)
from ipyelk.elements.elements import BaseProperties, EdgeSection
from ipyelk.elements.serialization import to_json
from ipyelk.schema import SCHEMA, validate_elk_json

from .test_label_schema import project

#: the schema definition that holds each region of the models
REGIONS: dict[type[BaseModel], str] = {
    Node: "AnyElkNode",
    Port: "AnyElkPort",
    Label: "AnyElkLabelWithProperties",
    Edge: "AnyElkEdgeWithProperties",
    EdgeSection: "ElkEdgeSection",
    shapes.Point: "ElkPoint",
    BaseProperties: "ElkProperties",
    shapes.BaseShape: "Shape",
}


def subclasses(cls: type) -> Iterator[type]:
    for sub in cls.__subclasses__():
        yield sub
        yield from subclasses(sub)


def wire_keys(cls: type[BaseModel]) -> set[str]:
    """The keys that ``model_dump`` can write for ``cls``."""
    fields = {name for name, field in cls.model_fields.items() if not field.exclude}
    return fields | set(cls.model_computed_fields)


def node_shapes(widget: IntSlider) -> list[shapes.NodeShape]:
    """One of each node shape class."""
    return [
        shapes.NodeShape(),
        shapes.Rect(),
        shapes.Circle(radius=7),
        shapes.Ellipse(rx=4, ry=3),
        shapes.Diamond(width=20, height=20),
        shapes.Comment(use=20),
        shapes.Path.from_list([(0, 0), (0, 10), (10, 0)], closed=True),
        shapes.SVG(use='<circle r="5"/>', x=5, y=5, width=10, height=10),
        shapes.Use(use="final_state"),
        shapes.Image(use="https://example.com/a.png"),
        shapes.ForeignObject(use="<b>bold</b>"),
        shapes.HTML(use="<i>slanted</i>"),
        shapes.Widget(widget=widget, delay=100),
    ]


def every_element(widget: IntSlider) -> Node:
    """A graph with every kind of element, every shape and hidden elements.

    The hidden node ``compound.inner`` has an edge, so the projection gives
    ``compound`` a slack port and the edge a slack edge.
    """
    root = Node(id="root", layoutOptions={"elk.direction": "RIGHT"})
    for i, shape in enumerate(node_shapes(widget)):
        root.add_child(Node(id=f"shape{i}", properties=NodeProperties(shape=shape)))
    icon = Label(
        id="icon",
        properties=LabelProperties(shape=shapes.Icon(use="class", width=8, height=8)),
    )
    labelled = root.add_child(
        Node(
            id="labelled",
            labels=[
                Label(id="title", text="Title", labels=[icon]),
                Label(
                    id="rule",
                    text="Rule",
                    properties=LabelProperties(
                        selectable=True,
                        tooltip="the full text",
                        separator=True,
                        separatorGap=2,
                        shape=shapes.LabelShape(width=30, height=10),
                    ),
                ),
                Label(id="gone", text="Gone", properties=LabelProperties(hidden=True)),
            ],
        )
    )
    port = labelled.add_port(
        Port(
            id="port",
            width=5,
            height=5,
            labels=[Label(id="port.label", text="p")],
            properties=PortProperties(shape=shapes.PortShape(use="dot")),
        ),
        key="port",
    )
    labelled.add_port(Port(id="hidden.port", properties=PortProperties(hidden=True)))
    compound = root.add_child(Node(id="compound"))
    inner = compound.add_child(Node(id="inner", properties=NodeProperties(hidden=True)))
    record = root.add_child(Record(id="record"))
    record.add_child(
        Compartment(id="compartment", bullet_shape=shapes.Icon(use="dot")).make_labels(
            headings=["Head"], content=["one", "two"]
        )
    )
    arrow = root.add_edge(port, root.children[0])
    arrow.id = "arrow"
    arrow.properties = EdgeProperties(
        shape=shapes.EdgeShape(start="dot", end="arrow"), cssClasses="arrow"
    )
    arrow.labels.append(Label(id="arrow.label", text="label"))
    arrow.sections = [
        EdgeSection(
            id="arrow.section",
            startPoint=shapes.Point(0, 0),
            endPoint=shapes.Point(10, 0),
            bendPoints=[shapes.Point(5, 5)],
            incomingShape="port",
            outgoingShape="shape0",
        )
    ]
    root.add_edge(inner, root.children[1]).id = "slack"
    labelled.set_laid_out(80, 40)
    labelled.x, labelled.y = 10, 20
    return root


@pytest.fixture
def widget() -> Iterator[IntSlider]:
    slider = IntSlider()
    yield slider
    slider.close()


@pytest.mark.parametrize(("model", "definition"), REGIONS.items())
def test_every_model_key_is_in_the_schema(model: type[BaseModel], definition: str):
    """No field of a model, or of a subclass in ipyelk, is missing in the schema."""
    allowed = set(SCHEMA["definitions"][definition]["properties"])
    missing = {
        cls.__qualname__: sorted(wire_keys(cls) - allowed)
        for cls in [model, *subclasses(model)]
        if cls.__module__.startswith("ipyelk.") and wire_keys(cls) - allowed
    }
    assert missing == {}


def test_every_shape_class_is_tested(widget: IntSlider):
    tested = {type(shape) for shape in node_shapes(widget)}
    found = {
        cls for cls in subclasses(shapes.NodeShape) if cls.__module__ == shapes.__name__
    }
    assert found - tested == set()


def test_the_view_payload_validates(widget: IntSlider):
    """The payload the view shows: laid-out sizes and sections, no hidden elements."""
    assert validate_elk_json(to_json(every_element(widget), None))


def test_the_layout_payload_validates(widget: IntSlider):
    """The payload ``VisibilityPipe`` sends to ELK, with a slack port and edge."""
    wire = project(every_element(widget))
    compound = next(n for n in wire["children"] if n["id"] == "compound")
    (slack,) = compound["ports"]
    assert "slack-port" in slack["properties"]["cssClasses"]
    assert validate_elk_json(wire)


def other_shapes() -> list[tuple[str, shapes.BaseShape]]:
    """One of each port, label and edge shape, with the element kind that has it."""
    return [
        ("ports", shapes.PortShape(use="dot", width=5, height=5)),
        ("labels", shapes.LabelShape(width=30, height=10)),
        ("labels", shapes.Icon(use="class", width=8, height=8)),
        ("edges", shapes.EdgeShape(start="dot", end="arrow")),
    ]


def shaped(kind: str, shape: shapes.BaseShape) -> Node:
    """A root with one element of ``kind`` that has ``shape``."""
    child = Node(id="child")
    root = Node(id="root", children=[child])
    if kind == "children":
        child.properties = NodeProperties(shape=shape)
    elif kind == "ports":
        child.add_port(Port(id="port", properties=PortProperties(shape=shape)))
    elif kind == "labels":
        child.labels.append(Label(id="label", properties=LabelProperties(shape=shape)))
    else:
        edge = root.add_edge(child, child)
        edge.id = "edge"
        edge.properties = EdgeProperties(shape=shape)
    return root


def loaded_shape(root: Node, kind: str) -> shapes.BaseShape | None:
    child = root.children[0]
    elements = {"children": [child], "edges": root.edges}.get(kind)
    return (elements or getattr(child, kind))[0].properties.shape


def test_every_shape_class_has_a_json_type():
    """A new shape class needs an entry in ``SHAPE_TYPES`` to load from JSON."""
    found = {
        cls
        for cls in subclasses(shapes.BaseShape)
        if cls.__module__ == shapes.__name__
        and cls.model_fields["type"].default is not None
    }
    assert found - set(shapes.SHAPE_TYPES.values()) == {shapes.Circle}


def test_json_loads_the_class_of_every_shape(widget: IntSlider):
    """JSON loads each shape as the class of its ``type`` (#153), with the same
    JSON. ``Circle`` loads as ``Ellipse``, the class of ``node:round``.
    """
    cases = [("children", s) for s in node_shapes(widget)] + other_shapes()
    for kind, shape in cases:
        wire = to_json(shaped(kind, shape), None)
        back = convert_elkjson(json.loads(json.dumps(wire)))
        loaded = loaded_shape(back, kind)
        expected = shapes.Ellipse if isinstance(shape, shapes.Circle) else type(shape)
        assert type(loaded) is expected, kind
        assert to_json(back, None) == wire
        assert loaded is not shape
    widget_shape = loaded_shape(
        convert_elkjson(
            to_json(shaped("children", shapes.Widget(widget=widget)), None)
        ),
        "children",
    )
    assert widget_shape.widget is widget


def test_a_circle_loads_as_an_ellipse_of_the_same_size():
    wire = to_json(shaped("children", shapes.Circle(radius=7)), None)
    ellipse = loaded_shape(convert_elkjson(wire), "children")
    assert isinstance(ellipse, shapes.Ellipse)
    assert (ellipse.width, ellipse.height, ellipse.rx, ellipse.ry) == (14, 14, 0, 0)


def test_the_projection_keeps_the_shape_classes(widget: IntSlider):
    """``VisibilityPipe`` loads the tree it sends to ELK, with the same classes."""
    root = every_element(widget)
    with exclude_hidden, exclude_layout:
        data = root.model_dump()
    projected = convert_elkjson(data, VisIndex.from_els(root))
    loaded = [
        type(n.properties.shape) for n in projected.children[: len(node_shapes(widget))]
    ]
    expected = [type(s) for s in node_shapes(widget)]
    assert loaded == [shapes.Ellipse if c is shapes.Circle else c for c in expected]
    assert projected.children[12].properties.shape.widget is widget


@pytest.mark.parametrize(
    ("properties", "shape", "message"),
    [
        (NodeProperties, {"type": "label:icon", "use": "x"}, "Unexpected Subtype"),
        (NodeProperties, {"type": "node:path"}, "use\n  Field required"),
        (
            NodeProperties,
            {"type": "node:widget", "use": "no-such-id"},
            "widget\n  Field required",
        ),
    ],
)
def test_json_that_its_shape_class_rejects_does_not_load(properties, shape, message):
    with pytest.raises(ValidationError, match=message):
        properties.model_validate({"shape": shape})
