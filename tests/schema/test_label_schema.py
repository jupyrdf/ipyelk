# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from ipyelk.elements import Node, NodeProperties, exclude_hidden, exclude_layout
from ipyelk.elements.index import VisIndex
from ipyelk.elements.serialization import convert_elkjson, to_json
from ipyelk.schema.validator import ElkSchemaValidator


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
    root = Node(id="root")
    hidden = root.add_child(Node(id="hidden", properties=NodeProperties(hidden=True)))
    shown = root.add_child(Node(id="shown"))
    root.add_edge(hidden, shown).id = "edge"
    vis_index = VisIndex.from_els(root)
    with exclude_hidden, exclude_layout:
        visible = convert_elkjson(root.model_dump(), vis_index)

    ElkSchemaValidator.validate(to_json(visible, None))
