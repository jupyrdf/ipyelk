# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import jsonschema
import pytest

from ipyelk.elements import Node, NodeProperties, exclude_hidden, exclude_layout
from ipyelk.elements.index import VisIndex
from ipyelk.elements.serialization import convert_elkjson, to_json
from ipyelk.schema.validator import ElkSchemaValidator
from ipyelk.tools import ToggleCollapsedTool


def project(root: Node) -> dict:
    vis_index = VisIndex.from_els(root)
    with exclude_hidden, exclude_layout:
        visible = convert_elkjson(root.model_dump(), vis_index)
    wire = to_json(visible, None)
    assert wire is not None
    return wire


def test_label_label_schema():
    nested_label = {
        "id": "root",
        "labels": [
            {
                "id": "top_label",
                "text": "",
                "labels": [{"id": "nested_label", "text": "", "properties": {}}],
            }
        ],
    }

    ElkSchemaValidator.validate(nested_label)


def test_schema_accepts_a_slack_port_lookup_key():
    """``root > C > hc(hidden)``: the edge ``hc -> shown`` lands on a slack port on C."""
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    hidden = compound.add_child(Node(id="hc", properties=NodeProperties(hidden=True)))
    shown = root.add_child(Node(id="shown"))
    root.add_edge(hidden, shown).id = "edge"

    wire = project(root)

    (port,) = wire["children"][0]["ports"]
    assert port["id"] == "hc"
    assert port["properties"]["key"] == "hc"
    ElkSchemaValidator.validate(wire)


def test_schema_accepts_hidden_after_collapse_and_expand():
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    child = compound.add_child(Node(id="child"))
    tool = ToggleCollapsedTool()
    tool.toggle(child)
    tool.toggle(child)

    wire = project(root)

    assert wire["children"][0]["children"][0]["properties"]["hidden"] is False
    ElkSchemaValidator.validate(wire)


@pytest.mark.parametrize("properties", [{"hidden": "yes"}, {"unknown": True}])
def test_schema_rejects_bad_properties(properties):
    with pytest.raises(jsonschema.ValidationError):
        ElkSchemaValidator.validate({"id": "root", "properties": properties})
