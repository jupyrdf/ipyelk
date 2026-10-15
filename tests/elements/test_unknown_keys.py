# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""An unknown key is an error in user code and is ignored in ELK JSON (#153).

The elements, their properties and their shapes are closed: a key that they do
not have is usually a typo. The layout options stay open. ELK JSON from the
frontend, from ELK or from a file, and the attributes of a ``networkx`` graph,
load with ``from_wire``, which ignores the keys that the models do not have.
"""

from __future__ import annotations

import networkx as nx
import pytest
from pydantic import ValidationError

from ipyelk.elements import (
    Label,
    Node,
    NodeProperties,
    Port,
    convert_elkjson,
    shapes,
)
from ipyelk.elements.elements import EdgeSection
from ipyelk.elements.serialization import to_json
from ipyelk.loaders import NXLoader

EXTRA = "Extra inputs are not permitted"


def errors(error: pytest.ExceptionInfo[ValidationError]) -> dict[tuple, str]:
    return {e["loc"]: e["type"] for e in error.value.errors()}


def test_a_typo_in_an_element_raises():
    with pytest.raises(ValidationError, match=EXTRA) as error:
        Node(id="n", layoutOpshuns={"a": 1}, hieght=5)
    assert errors(error) == {
        ("layoutOpshuns",): "extra_forbidden",
        ("hieght",): "extra_forbidden",
    }


@pytest.mark.parametrize(
    ("make", "loc"),
    [
        (
            lambda: Label(text="l", properties={"selectible": True}),
            ("properties", "selectible"),
        ),
        # ``selectable`` is a field of ``LabelProperties``, not of ``Label``
        (lambda: Label(text="l", selectable=True), ("selectable",)),
        (lambda: NodeProperties(cssClass="a"), ("cssClass",)),
        (
            lambda: Port(id="p", properties={"shape": {"type": "port", "us": "x"}}),
            ("properties", "shape", "us"),
        ),
        (lambda: shapes.Circle(raduis=7), ("raduis",)),
        # a field of another shape class: ``start`` is a field of ``EdgeShape``
        (lambda: shapes.Rect(start="arrow"), ("start",)),
        (lambda: shapes.EdgeShape(use="arrow"), ("use",)),
        (
            lambda: EdgeSection(
                id="s", startPoint=shapes.Point(0, 0), endPoint={}, end=1
            ),
            ("end",),
        ),
    ],
)
def test_a_typo_in_a_part_of_an_element_raises(make, loc):
    with pytest.raises(ValidationError, match=EXTRA) as error:
        make()
    assert errors(error) == {loc: "extra_forbidden"}


def test_a_typo_on_assignment_raises():
    node = Node(id="n")
    with pytest.raises(ValidationError, match=EXTRA):
        node.properties = {"cssClass": "a"}
    with pytest.raises(ValidationError, match=EXTRA):
        node.properties.shape = {"type": "node:round", "radius": 7}


def test_layout_options_stay_open():
    node = Node(id="n", layoutOptions={"made.up.option": 1})
    assert node.layoutOptions == {"made.up.option": "1"}


def test_elk_json_ignores_the_keys_that_the_models_do_not_have():
    """The frontend and ELK write keys that the models do not have."""
    a, b = Node(id="a"), Node(id="b")
    root = Node(id="root", children=[a, b])
    root.add_edge(a, b).id = "e"
    wire = to_json(root, None)
    extra = {"$H": 1, "made_up": True}
    wire.update(extra)
    wire["children"][0].update(extra, labels=[{"id": "l", "text": "l", **extra}])
    edge = wire["edges"][0]
    edge.update(extra, container="root", junctionPoints=[{"x": 0, "y": 0}])
    edge["sections"] = [
        {
            "id": "s",
            "startPoint": {"x": 0, "y": 0, **extra},
            "endPoint": {"x": 1, "y": 1},
            "labels": [],
            **extra,
        }
    ]
    edge["properties"] = {"isSymbol": False, "shape": {"type": "edge", **extra}}

    back = convert_elkjson(wire)

    assert to_json(back, None)["edges"][0]["sections"][0]["endPoint"] == {
        "x": 1,
        "y": 1,
    }
    assert back.children[0].labels[0].text == "l"
    assert isinstance(back.edges[0].properties.shape, shapes.EdgeShape)


def test_networkx_attributes_pass_through():
    """The ``networkx`` loader ignores the attributes that an element does not have."""
    graph = nx.MultiDiGraph()
    graph.add_node("x", weight=3, labels=[{"text": "x"}])
    graph.add_edge("x", "y", weight=1, sourcePort="out")
    mark = NXLoader().load(graph=graph)
    try:
        (x,) = [n for n in mark.value.children if n.id == "x"]
        assert x.labels[0].text == "x"
        assert len(x.ports) == 1
    finally:
        mark.close()
