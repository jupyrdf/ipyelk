"""Layout options are a ``dict[str, str]`` on elements and option widgets."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from traitlets import TraitError

from ipyelk.elements import Label, Node
from ipyelk.elements import layout_options as opt


def test_node_dump_is_json() -> None:
    node = Node(
        id="n",
        labels=[Label(text="n", layoutOptions={opt.NodeLabelPlacement.identifier: ""})],
        layoutOptions={opt.Direction.identifier: "DOWN"},
    )
    dumped = json.loads(json.dumps(node.model_dump(mode="json")))
    assert dumped["layoutOptions"] == {"org.eclipse.elk.direction": "DOWN"}


def test_options_widget_value_is_strings() -> None:
    widget = opt.OptionsWidget(
        options=[opt.Direction(value="DOWN"), opt.NodeSpacing(spacing=4)]
    )
    assert widget.value == {
        "org.eclipse.elk.direction": "DOWN",
        "org.eclipse.elk.spacing.nodeNode": "4.0",
    }
    with pytest.raises(TraitError):
        widget.value = {"org.eclipse.elk.direction": 1}


def test_bool_and_number_values_become_strings() -> None:
    node = Node(layoutOptions={"elk.spacing.nodeNode": 20, "elk.x": 1.5, "elk.y": True})
    assert node.layoutOptions == {
        "elk.spacing.nodeNode": "20",
        "elk.x": "1.5",
        "elk.y": "true",
    }


@pytest.mark.parametrize(
    "options",
    [{1: "DOWN"}, {"elk.direction": None}, {"elk.direction": ["DOWN"]}],
    ids=["int-key", "none-value", "list-value"],
)
def test_other_keys_and_values_are_rejected(options: dict) -> None:
    with pytest.raises(ValidationError):
        Node(layoutOptions=options)
    node = Node()
    with pytest.raises(ValidationError):
        node.layoutOptions = options
