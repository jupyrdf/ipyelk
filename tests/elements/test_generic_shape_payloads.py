# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A generic shape class with the type string of a built-in class validates ``use`` as
that class does (#244): ``NodeShape(type="node:comment", use="abc")`` raises, as
``Comment(use="abc")`` does. A custom type string keeps a string ``use``.
"""

from __future__ import annotations

from collections.abc import Iterator

import jsonschema
import pytest
from ipywidgets import IntSlider
from pydantic import Field, ValidationError, field_validator

from ipyelk.elements import (
    Label,
    LabelProperties,
    Node,
    Port,
    PortProperties,
    convert_elkjson,
    shapes,
)
from ipyelk.elements.serialization import to_json
from ipyelk.schema import validate_elk_json

#: each generic class, and the type strings of other classes that it accepts
GENERIC = {
    shapes.NodeShape: [
        "node",
        "node:path",
        "node:svg",
        "node:round",
        "node:diamond",
        "node:comment",
        "node:use",
        "node:image",
        "node:foreignobject",
        "node:widget",
        "node:html",
    ],
    shapes.LabelShape: ["label:icon"],
    shapes.ElementShape: ["port", "label"],
}

#: a payload that the class of each type string rejects, and the error type at ``use``
REJECTED = {
    "node": ("x", "none_required"),
    "node:path": ("hello", "string_pattern_mismatch"),
    "node:svg": (None, "missing"),
    "node:round": ("x", "none_required"),
    "node:diamond": ("x", "none_required"),
    "node:comment": ("abc", "float_parsing"),
    "node:use": ("", "string_too_short"),
    "node:image": ("", "string_too_short"),
    "node:foreignobject": (None, "missing"),
    "node:html": (None, "missing"),
    "label:icon": (None, "missing"),
    "port": ("", "string_too_short"),
    "label": ("", "string_too_short"),
}

#: a payload that the class of each type string accepts
VALID = {
    "node": None,
    "node:path": "M0,0 L1,1",
    "node:svg": "<g/>",
    "node:round": None,
    "node:diamond": None,
    "node:comment": 20,
    "node:use": "dot",
    "node:image": "a.png",
    "node:foreignobject": "<b/>",
    "node:html": "<b/>",
    "label:icon": "dot",
    "port": "dot",
    "label": "dot",
}

#: the type strings whose class requires ``use``
REQUIRED = {
    "node:path",
    "node:svg",
    "node:use",
    "node:image",
    "node:foreignobject",
    "node:html",
    "label:icon",
}

CASES = [(cls, tag) for cls, tags in GENERIC.items() for tag in tags if tag in REJECTED]


def case_id(case: tuple) -> str:
    return f"{case[0].__name__}-{case[1]}"


def use_errors(error: ValidationError) -> list[str]:
    return [e["type"] for e in error.errors() if e["loc"][-1:] == ("use",)]


@pytest.mark.parametrize(("cls", "tag"), CASES, ids=map(case_id, CASES))
def test_construction_checks_the_payload_of_the_type(cls, tag):
    use, kind = REJECTED[tag]
    with pytest.raises(ValidationError) as info:
        cls(type=tag, use=use)
    assert use_errors(info.value) == [kind]


@pytest.mark.parametrize(("cls", "tag"), CASES, ids=map(case_id, CASES))
def test_json_checks_the_payload_of_the_type(cls, tag):
    use, kind = REJECTED[tag]
    with pytest.raises(ValidationError) as info:
        cls.model_validate({"type": tag, "use": use})
    assert use_errors(info.value) == [kind]
    with pytest.raises(ValidationError) as info:
        cls.model_validate_json(f'{{"type": "{tag}", "use": {to_json_value(use)}}}')
    assert use_errors(info.value) == [kind]


def to_json_value(use: object) -> str:
    return "null" if use is None else f'"{use}"'


@pytest.mark.parametrize(("cls", "tag"), CASES, ids=map(case_id, CASES))
def test_assignment_checks_the_payload_of_the_type(cls, tag):
    use, kind = REJECTED[tag]
    shape = cls(type=tag, use=VALID[tag])
    before = dict(shape.__dict__)
    with pytest.raises(ValidationError) as info:
        shape.use = use
    assert use_errors(info.value) == [kind]
    assert shape.__dict__ == before


@pytest.mark.parametrize(("cls", "tag"), CASES, ids=map(case_id, CASES))
def test_a_new_type_checks_the_payload_that_the_shape_has(cls, tag):
    use, kind = REJECTED[tag]
    shape = cls() if use is None else cls(use=use)
    before = dict(shape.__dict__)
    with pytest.raises(ValidationError) as info:
        shape.type = tag
    assert use_errors(info.value) == [kind]
    assert shape.__dict__ == before


@pytest.mark.parametrize("tag", sorted(REQUIRED), ids=str)
def test_a_type_that_requires_a_payload_requires_it_on_a_generic_class(tag):
    cls = shapes.LabelShape if tag.startswith("label") else shapes.NodeShape
    with pytest.raises(ValidationError) as info:
        cls(type=tag)
    assert use_errors(info.value) == ["missing"]


def test_the_payload_takes_the_type_of_the_class():
    """A notch in a string, as 2.x wrote it, loads as a number, as in a ``Comment``."""
    shape = shapes.NodeShape(type="node:comment", use="20")
    assert shape.use == 20
    assert shape.model_dump(mode="json", exclude_none=True) == {
        "type": "node:comment",
        "use": 20.0,
    }
    shape.use = "5"
    assert shape.use == 5
    shape = shapes.NodeShape(use="20")
    shape.type = "node:comment"
    assert shape.use == 20
    with pytest.raises(ValidationError) as info:
        shape.type = None  # a custom payload is a string
    assert use_errors(info.value) == ["string_type"]
    assert (shape.type, shape.use) == ("node:comment", 20.0)


@pytest.mark.parametrize(
    ("cls", "data"),
    [
        (shapes.NodeShape, {"type": "node:comment"}),
        (shapes.NodeShape, {"type": "node:comment", "use": None}),
        (shapes.NodeShape, {"type": "node:comment", "use": 0}),
        (shapes.NodeShape, {"type": "node"}),
        (shapes.NodeShape, {"type": "node:round", "width": 10}),
        (shapes.NodeShape, {"type": "node:path", "use": "M0,0 L1,1"}),
        (shapes.NodeShape, {"type": "node:svg", "use": "<g/>"}),
        (shapes.NodeShape, {"type": "node:use", "use": "dot"}),
        (shapes.LabelShape, {"type": "label:icon", "use": "dot"}),
        (shapes.ElementShape, {"type": "port", "use": "dot"}),
        (shapes.ElementShape, {"type": "label"}),
    ],
)
def test_a_valid_payload_keeps_its_value(cls, data):
    shape = cls(**data)
    assert shape.model_dump(exclude_unset=True) == data


@pytest.mark.parametrize(
    "data",
    [
        {"use": "anything"},
        {"use": ""},
        {"type": "node:star", "use": "anything"},
        {"type": "node:star"},
    ],
)
def test_a_custom_type_keeps_a_string_payload(data, json_classes):
    class Star(shapes.NodeShape):
        type: str = "node:star"
        loads_from_json = False

    shape = shapes.NodeShape(**data)
    assert shape.model_dump(exclude_unset=True) == data
    with pytest.raises(ValidationError) as info:
        shapes.NodeShape(**{**data, "use": 20})
    assert use_errors(info.value) == ["string_type"]


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


def test_the_class_of_a_custom_type_checks_its_payload(json_classes):
    class Star(shapes.NodeShape):
        type: str = "node:star"
        use: shapes.SymbolId = "star"

    with pytest.raises(ValidationError) as info:
        shapes.NodeShape(type="node:star", use="")
    assert use_errors(info.value) == ["string_too_short"]
    assert shapes.NodeShape(type="node:star", use="dot").use == "dot"
    assert Star().use == "star"


def test_a_built_in_class_keeps_its_own_payload(json_classes):
    """The check uses the class of a type string only for a shape of another class
    with that type string. A replaced ``node:round`` does not change ``Circle``.
    """
    with pytest.warns(UserWarning, match="replaces"):

        class Oval(shapes.NodeShape):
            type: str = "node:round"
            use: str = "oval"

    with pytest.raises(ValidationError) as info:
        shapes.Circle(use="x")
    assert use_errors(info.value) == ["none_required"]
    with pytest.raises(ValidationError) as info:
        shapes.Ellipse(use="x")
    assert use_errors(info.value) == ["none_required"]
    assert shapes.NodeShape(type="node:round", use="x").use == "x"


@pytest.fixture
def closed_widget() -> str:
    """The ``model_id`` of a closed widget."""
    slider = IntSlider()
    model_id = slider.model_id
    slider.close()
    return model_id


def test_a_widget_shape_without_its_widget_still_loads_from_elk_json(closed_widget):
    """The wire fallback of #239 builds ``NodeShape(type="node:widget")``, which takes
    the ``use`` of a ``Widget``: any string.
    """
    wire = {
        "id": "root",
        "children": [
            {
                "id": "n",
                "properties": {
                    "shape": {"type": "node:widget", "use": closed_widget, "delay": 5}
                },
            }
        ],
    }
    with pytest.warns(UserWarning, match="loads as a NodeShape"):
        root = convert_elkjson(wire)
    shape = root.children[0].properties.shape
    assert type(shape) is shapes.NodeShape
    assert shape.use == closed_widget
    again = to_json(root, None)
    assert validate_elk_json(again)
    assert again["children"][0]["properties"]["shape"] == {
        "type": "node:widget",
        "use": closed_widget,
        "delay": 5,
    }
    with pytest.warns(UserWarning, match="loads as a NodeShape"):
        assert convert_elkjson(again).children[0].properties.shape == shape
    assert shapes.NodeShape(type="node:widget", use="abc").use == "abc"
    with pytest.raises(ValidationError) as info:
        shapes.NodeShape(type="node:widget", use=5)
    assert use_errors(info.value) == ["string_type"]


#: payloads to try on each type string, of each kind that a payload type checks
PAYLOADS = [None, "", "x", "dot", "20", "-1", "abc", "M0,0 L1,1", "<b/>", 20, -1, True]

#: the generic classes, each with every type string of another class that it accepts
CHECKED = [(cls, tag) for cls, tags in GENERIC.items() for tag in tags]


def kind_of(tag: str) -> str:
    """The key of the elements that take a shape with the type string ``tag``."""
    if tag == "port":
        return "ports"
    return "labels" if tag.startswith("label") else "children"


def wire_with(tag: str, shape: dict | None) -> dict:
    """The ELK JSON of a root with one element that has the JSON ``shape``."""
    kind = kind_of(tag)
    root = Node(id="root")
    child = Node(id="child")
    root.add_child(child)
    if kind == "ports":
        child.add_port(Port(id="port", properties=PortProperties()))
    elif kind == "labels":
        child.labels.append(Label(id="label", properties=LabelProperties()))
    wire = to_json(root, None)
    element = wire["children"][0]
    if kind != "children":
        element = element[kind][0]
    element.setdefault("properties", {})["shape"] = shape
    return wire


@pytest.mark.parametrize(("cls", "tag"), CHECKED, ids=map(case_id, CHECKED))
def test_a_valid_shape_writes_valid_json(cls, tag):
    """Each payload that Python accepts on a generic class passes ``elkschema.json``."""
    accepted = 0
    for use in PAYLOADS:
        try:
            shape = cls(type=tag, use=use)
        except ValidationError:
            continue
        accepted += 1
        if tag == "node:widget" and use is None:
            # the schema requires the model_id, and a Widget writes it. A NodeShape
            # keeps the optional use of a Widget, so that ELK JSON without it loads.
            continue
        data = shape.model_dump(mode="json", exclude_none=True)
        assert validate_elk_json(wire_with(tag, data)), (tag, use)
    assert accepted


@pytest.mark.parametrize(("cls", "tag"), CHECKED, ids=map(case_id, CHECKED))
def test_python_and_the_schema_accept_the_same_strings(cls, tag):
    """A generic class accepts a string payload if the schema does. The notch is the
    exception: Python reads a string of a number, as 2.x wrote it.
    """
    for use in PAYLOADS:
        if not isinstance(use, str) or tag == "node:comment":
            continue
        data = {"type": tag, "use": use}
        try:
            validate_elk_json(wire_with(tag, data))
        except jsonschema.ValidationError:
            schema_ok = False
        else:
            schema_ok = True
        try:
            cls(**data)
        except ValidationError:
            python_ok = False
        else:
            python_ok = True
        assert python_ok == schema_ok, data


def test_a_port_type_of_your_own_requires_its_payload(json_classes):
    class Star(shapes.PortShape):
        type: str = "port:star"
        use: shapes.SymbolId = Field(...)

    with pytest.raises(ValidationError) as info:
        shapes.PortShape(type="port:star")
    assert use_errors(info.value) == ["missing"]
    assert shapes.PortShape(type="port:star", use="dot").use == "dot"


def test_a_class_without_use_gives_no_payload_type(json_classes):
    """A type string that a class without ``use`` loads keeps the string ``use``."""

    class Fancy(shapes.EdgeShape):
        type: str = "edge:fancy"

    class FancyNode(shapes.NodeShape):
        type: str = "edge:fancy"
        loads_from_json = False

    assert shapes.NodeShape(type="edge:fancy", use="x").use == "x"


def test_only_the_type_of_the_payload_applies(json_classes):
    """The generic class takes the annotation and constraints of ``use``, but not a
    ``field_validator`` of the class of the type string.
    """

    class Star(shapes.NodeShape):
        type: str = "node:star"
        use: str = "star"

        @field_validator("use")
        @classmethod
        def starts_with_s(cls, value: str) -> str:
            if not value.startswith("s"):
                raise ValueError("not a star")
            return value

    with pytest.raises(ValidationError):
        Star(use="abc")
    assert shapes.NodeShape(type="node:star", use="abc").use == "abc"
