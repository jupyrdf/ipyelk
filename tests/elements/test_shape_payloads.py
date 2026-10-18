# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Each shape validates its typed ``use`` payload (#148): at construction, on
assignment and when JSON loads, with an error at the ``use`` field.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import pytest
from ipywidgets import IntSlider
from pydantic import ValidationError

from ipyelk.elements import (
    LabelProperties,
    NodeProperties,
    PortProperties,
    convert_elkjson,
    shapes,
)

#: a payload that each class rejects, and the error type at ``use``
REJECTED = [
    (shapes.Comment, "abc", "float_parsing"),
    (shapes.Comment, -1, "greater_than_equal"),
    (shapes.Comment, math.nan, "finite_number"),
    (shapes.Comment, "inf", "finite_number"),
    (shapes.Comment, True, "value_error"),
    (shapes.Comment, None, "float_type"),
    (shapes.Path, "hello", "string_pattern_mismatch"),
    (shapes.Path, "", "string_pattern_mismatch"),
    (shapes.Path, 5, "string_type"),
    (shapes.Use, "", "string_too_short"),
    (shapes.Icon, "", "string_too_short"),
    (shapes.PortShape, "", "string_too_short"),
    (shapes.LabelShape, "", "string_too_short"),
    (shapes.Image, "", "string_too_short"),
    (shapes.SVG, None, "string_type"),
    (shapes.HTML, None, "string_type"),
    (shapes.ForeignObject, 1, "string_type"),
    (shapes.Rect, "x", "none_required"),
    (shapes.Diamond, "x", "none_required"),
    (shapes.Ellipse, "x", "none_required"),
    (shapes.Circle, "x", "none_required"),
]

#: a valid payload of each class with a ``use`` that has a meaning
VALID = {
    shapes.Comment: 20,
    shapes.Path: "M0,0 L20,20",
    shapes.Use: "final_state",
    shapes.Icon: "class",
    shapes.PortShape: "dot",
    shapes.LabelShape: "dot",
    shapes.Image: "https://example.com/image.png",
    shapes.SVG: '<circle r="5"/>',
    shapes.HTML: "<b>x</b>",
    shapes.ForeignObject: "<input/>",
    shapes.Rect: None,
    shapes.Diamond: None,
    shapes.Ellipse: None,
    shapes.Circle: None,
}


def use_errors(error: ValidationError) -> list[str]:
    return [e["type"] for e in error.errors() if e["loc"][-1:] == ("use",)]


def case_id(case: tuple) -> str:
    return f"{case[0].__name__}-{case[1]!r}"


@pytest.mark.parametrize(("cls", "use", "kind"), REJECTED, ids=map(case_id, REJECTED))
def test_construction_rejects_the_payload(cls, use, kind):
    with pytest.raises(ValidationError) as info:
        cls(use=use)
    assert use_errors(info.value) == [kind]


@pytest.mark.parametrize(("cls", "use", "kind"), REJECTED, ids=map(case_id, REJECTED))
def test_assignment_rejects_the_payload_and_keeps_the_value(cls, use, kind):
    shape = cls(use=VALID[cls])
    before = shape.use
    with pytest.raises(ValidationError) as info:
        shape.use = use
    assert use_errors(info.value) == [kind]
    assert shape.use == before


@pytest.mark.parametrize(("cls", "use", "kind"), REJECTED, ids=map(case_id, REJECTED))
def test_json_rejects_the_payload(cls, use, kind):
    shape = {"type": cls.model_fields["type"].default, "use": use}
    if cls is shapes.Circle:  # JSON loads `node:round` as an Ellipse
        with pytest.raises(ValidationError) as info:
            cls.model_validate(shape)
    else:
        properties = {
            shapes.PortShape: PortProperties,
            shapes.LabelShape: LabelProperties,
            shapes.Icon: LabelProperties,
        }.get(cls, NodeProperties)
        with pytest.raises(ValidationError) as info:
            properties.model_validate({"shape": shape})
    assert use_errors(info.value) == [kind]


def test_legacy_payloads_load_with_the_same_meaning():
    """The 2.x calls and JSON of #148 keep working."""
    assert shapes.Comment(use=15).use == 15
    assert shapes.Comment(use="15").use == 15
    assert shapes.Comment().use == 15
    assert shapes.Path(use="M0,0 L20,20").use == "M0,0 L20,20"
    assert shapes.Image(use="https://example.com/image.png").use.endswith(".png")
    assert shapes.Path.from_list([(0, 0), (1.5, -2e-05)], closed=True).use
    saved = {"type": "node:comment", "use": "20"}  # what 2.x wrote
    root = convert_elkjson({
        "id": "root",
        "children": [{"id": "a", "properties": {"shape": saved}}],
    })
    assert root.children[0].properties.shape.use == 20


def test_a_comment_writes_its_notch_as_a_number():
    assert shapes.Comment(use=0).model_dump(mode="json")["use"] == 0
    assert shapes.Comment().model_dump(mode="json", exclude_none=True) == {
        "type": "node:comment",
        "use": 15,
    }


@pytest.fixture
def widget() -> Iterator[IntSlider]:
    slider = IntSlider()
    yield slider
    slider.close()


def test_a_widget_shape_rejects_a_use_of_another_model_id(widget):
    with pytest.raises(ValidationError, match="is not the model_id"):
        shapes.Widget(widget=widget, use="other")
    shape = shapes.Widget(widget=widget, use=widget.model_id)
    with pytest.raises(ValidationError, match="leave use out"):
        shape.use = "other"
    shape.delay = 5  # another field still assigns
    assert shape.model_dump()["use"] == widget.model_id


def every_shape(widget: IntSlider) -> list[shapes.BaseShape]:
    return [
        *(cls(use=use) for cls, use in VALID.items()),
        shapes.NodeShape(use="custom"),
        shapes.EdgeShape(start="dot", end="arrow"),
        shapes.Widget(widget=widget, delay=100),
    ]


def test_serialization_does_not_change_the_shape(widget):
    for shape in every_shape(widget):
        before = (dict(shape.__dict__), set(shape.model_fields_set))
        shape.model_dump()
        shape.model_dump(mode="json", exclude_none=True)
        assert (dict(shape.__dict__), shape.model_fields_set) == before, shape
