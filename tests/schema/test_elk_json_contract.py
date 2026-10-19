# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The models agree with ``elkschema.json``, the ELK JSON schema of the frontend.

The TypeScript types of the frontend generate ``elkschema.json``.
These tests are the drift check of #131 and #153: every key the models can write
is in the schema, and a payload with every kind of element validates.
"""

from __future__ import annotations

import json
import re
import warnings
from collections.abc import Iterator
from pathlib import Path

import jsonschema
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
from ipyelk.pipes import MarkElementWidget
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
    # the variant of the other type strings has every key that a shape can have
    shapes.BaseShape: "CustomShape",
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


#: the class that JSON loads for each type string of ipyelk
BUILT_IN_TYPES = {
    "edge": shapes.EdgeShape,
    "port": shapes.PortShape,
    "label": shapes.LabelShape,
    "label:icon": shapes.Icon,
    "node": shapes.Rect,
    "node:path": shapes.Path,
    "node:svg": shapes.SVG,
    "node:round": shapes.Ellipse,
    "node:diamond": shapes.Diamond,
    "node:comment": shapes.Comment,
    "node:use": shapes.Use,
    "node:image": shapes.Image,
    "node:foreignobject": shapes.ForeignObject,
    "node:widget": shapes.Widget,
    "node:html": shapes.HTML,
}


#: the view types of ``di-config.ts`` that no shape class has
FRONTEND_ONLY_TYPES = {"graph", "junction", "symbol", "node:compartment"}

DI_CONFIG = Path(__file__).parents[2] / "js/sprotty/di-config.ts"


@pytest.fixture
def json_classes() -> Iterator[dict[str, type[shapes.BaseShape]]]:
    """``BaseShape.json_classes``. At the end of the test, it removes the classes the
    test added.
    """
    classes = shapes.BaseShape.json_classes
    before = dict(classes)
    yield classes
    classes.clear()
    classes.update(before)


def schema_variant(tag: str) -> dict:
    """The definition in the ``Shape`` union of the schema for the type ``tag``."""
    definitions = SCHEMA["definitions"]
    for ref in definitions["Shape"]["anyOf"]:
        variant = definitions[ref["$ref"].rsplit("/", 1)[1]]
        if variant["properties"]["type"].get("const") == tag:
            return variant
    raise KeyError(tag)


def payload_type(fragment: dict | None) -> dict | None:
    """The type and the constraints of a field schema, from either side."""
    if fragment is None:
        return None
    if "$ref" in fragment:
        fragment = SCHEMA["definitions"][fragment["$ref"].rsplit("/", 1)[1]]
    # pydantic writes an optional field as a union with null
    options = [f for f in fragment.get("anyOf", [fragment]) if f.get("type") != "null"]
    (fragment,) = options
    keys = {"type", "minimum", "minLength", "pattern"}
    return {key: value for key, value in fragment.items() if key in keys}


@pytest.mark.parametrize(("tag", "cls"), BUILT_IN_TYPES.items())
def test_each_built_in_type_has_its_payload_in_the_schema(tag, cls):
    """The ``use`` of each class has the type and the constraints of the schema
    variant of its type string, and the variant requires it if the class does (#148).
    """
    variant = schema_variant(tag)
    assert wire_keys(cls) <= set(variant["properties"])
    python = cls.model_json_schema(mode="serialization")["properties"].get("use")
    on_wire = "use" in wire_keys(cls)
    assert payload_type(python if on_wire else None) == payload_type(
        variant["properties"].get("use")
    )
    if on_wire:
        # a Widget writes the model_id of its widget: the field is never set by hand
        required = cls.model_fields["use"].is_required() or cls is shapes.Widget
        assert required == ("use" in variant.get("required", []))


@pytest.mark.parametrize(
    ("shape", "valid"),
    [
        ({"type": "node:comment", "use": 20}, True),
        ({"type": "node:comment", "use": "abc"}, False),
        ({"type": "node:comment", "use": -1}, False),
        ({"type": "node:path", "use": "M0,0 L1,1"}, True),
        ({"type": "node:path", "use": "hello"}, False),
        ({"type": "node:use", "use": ""}, False),
        ({"type": "node", "use": "x"}, False),
        ({"type": "node:star", "use": "x"}, True),
        ({"use": "x"}, True),
    ],
)
def test_the_schema_checks_the_payload_of_each_type(shape, valid):
    """A built-in type string takes only its own payload. A custom type string
    takes any string payload, which its own view reads.
    """
    root = {"id": "root", "children": [{"id": "a", "properties": {"shape": shape}}]}
    if valid:
        assert validate_elk_json(root)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validate_elk_json(root)


def test_every_shape_class_has_a_json_type():
    """Each shape class with a type string adds itself to ``json_classes``, so JSON
    loads it, except ``Circle``.
    """
    found = {
        cls
        for cls in subclasses(shapes.BaseShape)
        if cls.__module__ == shapes.__name__
        and cls.model_fields["type"].default is not None
    }
    assert found - set(shapes.BaseShape.json_classes.values()) == {shapes.Circle}


def test_each_built_in_type_has_its_class():
    built_in = {
        tag: cls
        for tag, cls in shapes.BaseShape.json_classes.items()
        if cls.__module__ == shapes.__name__
    }
    assert built_in == BUILT_IN_TYPES
    assert shapes.Circle not in shapes.BaseShape.json_classes.values()


def test_the_frontend_has_a_view_for_each_type():
    """The view types that ``di-config.ts`` registers are the type strings of the
    shape classes, and the frontend-only types.
    """
    source = DI_CONFIG.read_text(encoding="utf-8")
    views = set(re.findall(r"configureModelElement\(\s*context,\s*'([^']+)'", source))
    assert views == set(BUILT_IN_TYPES) | FRONTEND_ONLY_TYPES


def test_a_subclass_with_the_type_of_its_parent_does_not_add_itself(json_classes):
    class MyRect(shapes.Rect):
        pass

    class MyEllipse(shapes.Ellipse):
        type: str = "node:round"

    assert json_classes == BUILT_IN_TYPES


def test_a_class_that_does_not_load_from_json_does_not_add_itself(json_classes):
    class Star(shapes.NodeShape):
        type: str = "node:star"
        loads_from_json = False

    assert json_classes == BUILT_IN_TYPES


def test_a_second_class_for_a_type_warns_and_replaces_the_first(json_classes):
    message = (
        r"\.Oval replaces ipyelk\.elements\.shapes\.Ellipse as the class that loads"
        r" the shape type 'node:round'"
    )
    with pytest.warns(UserWarning, match=message):

        class Oval(shapes.NodeShape):
            type: str = "node:round"

    assert json_classes == {**BUILT_IN_TYPES, "node:round": Oval}


def test_a_renamed_class_replaces_the_old_name(json_classes):
    """A notebook cell that renames a class, and keeps its type, runs again."""

    class MyShape(shapes.NodeShape):
        type: str = "node:mine"

    with pytest.warns(UserWarning, match=r"\.MyShape2 replaces .*\.MyShape as"):

        class MyShape2(shapes.NodeShape):
            type: str = "node:mine"

    assert json_classes["node:mine"] is MyShape2


def test_the_same_class_defined_again_replaces_it_with_no_warning(json_classes):
    """A module reload, or a function that defines a class, defines the same class."""

    def define() -> type[shapes.NodeShape]:
        class Local(shapes.NodeShape):
            type: str = "node:local"

        return Local

    first, second = define(), define()  # pytest makes a warning an error
    assert first is not second
    assert json_classes["node:local"] is second


def test_a_new_shape_class_loads_from_json(json_classes):
    class Star(shapes.NodeShape):
        type: str = "node:star"

    assert json_classes == {**BUILT_IN_TYPES, "node:star": Star}
    loaded = loaded_shape(
        convert_elkjson(to_json(shaped("children", Star()), None)), "children"
    )
    assert type(loaded) is Star


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
    ],
)
def test_json_that_its_shape_class_rejects_does_not_load(properties, shape, message):
    with pytest.raises(ValidationError, match=message):
        properties.model_validate({"shape": shape})


def closed_widget_json() -> dict:
    """The JSON of a root with a ``Widget`` node, after its widget closes."""
    slider = IntSlider()
    shape = shapes.Widget(widget=slider, delay=100, width=20, height=10)
    wire = to_json(shaped("children", shape), None)
    slider.close()
    return wire


@pytest.mark.parametrize("model_id", ["closed", "no-such-id"])
def test_a_widget_shape_with_no_open_widget_loads_as_a_node_shape(model_id):
    """A closed widget, or JSON from another kernel, loads with the same JSON (#233)."""
    wire = closed_widget_json()
    if model_id != "closed":
        wire["children"][0]["properties"]["shape"]["use"] = model_id
    shape_json = dict(wire["children"][0]["properties"]["shape"])
    with pytest.warns(UserWarning, match="No open widget has the model_id") as caught:
        back = convert_elkjson(json.loads(json.dumps(wire)))
    assert len(caught) == 1
    loaded = loaded_shape(back, "children")
    assert type(loaded) is shapes.NodeShape
    assert loaded.model_dump(mode="json", exclude_none=True) == shape_json
    assert to_json(back, None) == wire


@pytest.mark.parametrize(
    "build",
    [
        lambda shape: NodeProperties(shape=shape),
        lambda shape: NodeProperties.model_validate({"shape": shape}),
        lambda shape: Node(id="a", properties={"shape": shape}),
    ],
    ids=["NodeProperties", "model_validate", "Node"],
)
def test_user_code_with_a_widget_shape_and_no_open_widget_raises(build):
    """Only ELK JSON loads a ``NodeShape`` in place of the ``Widget``: user code that
    builds a ``Widget`` with no widget raises, and does not warn.
    """
    shape = closed_widget_json()["children"][0]["properties"]["shape"]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValidationError, match="widget\n  Field required"):
            build(shape)


def test_a_layout_result_with_a_closed_widget_loads():
    """The value that comes back from the frontend after a layout still loads."""
    wire = closed_widget_json()
    wire["children"][0]["x"] = 15  # laid out
    outlet = MarkElementWidget()
    outlet.sync_value()  # as the outlet of a browser stage does (#235)
    with pytest.warns(UserWarning, match="No open widget has the model_id"):
        outlet.set_state({"value": wire})
    assert outlet.value.children[0].x == 15
    assert type(outlet.value.children[0].properties.shape) is shapes.NodeShape
