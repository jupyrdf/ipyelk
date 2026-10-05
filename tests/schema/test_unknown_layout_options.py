"""The opt-in report of layout option keys that ELK ignores (#115)."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import asyncio
import warnings

import pytest

from ipyelk.elements import Label, Node
from ipyelk.pipes import MarkElementWidget, ValidationPipe
from ipyelk.schema import elk_catalog, unknown_layout_options

KNOWN = [
    "org.eclipse.elk.direction",
    "elk.direction",
    "spacing.nodeNode",
    "layered.considerModelOrder.strategy",
    "considerModelOrder.strategy",
]
UNKNOWN = [
    "org.eclipse.elk.edge.edgeNode",
    "\torg.eclipse.elk.contentAlignment",
    "elk.spacing.labelPort",
    "nodeNode.spacing",
    # ambiguous: also ends `org.eclipse.elk.layered.priority.direction`
    "direction",
]


def test_catalog_is_read_once() -> None:
    assert elk_catalog() is elk_catalog()


def test_unknown_layout_options() -> None:
    assert unknown_layout_options(KNOWN) == []
    assert unknown_layout_options([*KNOWN, *UNKNOWN]) == UNKNOWN
    assert unknown_layout_options({"elk.edge.edgeNode": "10"}) == ["elk.edge.edgeNode"]


def run_pipe(root: Node, **kwargs) -> ValidationPipe:
    pipe = ValidationPipe(**kwargs)
    pipe.inlet = MarkElementWidget(value=root)
    asyncio.run(pipe.run())
    return pipe


def graph() -> Node:
    root = Node(id="root", layoutOptions={"elk.direction": "DOWN", "direction": "UP"})
    label = Label(id="a.l", text="a", layoutOptions={"elk.nodeLabels.placment": "X"})
    root.add_child(Node(id="a", labels=[label]))
    return root


def test_check_is_off_by_default() -> None:
    with warnings.catch_warnings():
        # the check warns with UserWarning; other categories keep pytest's filters
        warnings.simplefilter("error", UserWarning)
        pipe = run_pipe(graph())
    assert not pipe.check_layout_options
    assert pipe.layout_options_report == {}


def test_check_reports_and_warns() -> None:
    with pytest.warns(UserWarning, match="direction"):
        pipe = run_pipe(graph(), check_layout_options=True)
    assert pipe.layout_options_report == {
        "root": ["direction"],
        "a.l": ["elk.nodeLabels.placment"],
    }


def test_check_is_quiet_when_every_key_is_known() -> None:
    root = Node(id="root", layoutOptions={"elk.direction": "DOWN"})
    with warnings.catch_warnings():
        # the check warns with UserWarning; other categories keep pytest's filters
        warnings.simplefilter("error", UserWarning)
        pipe = run_pipe(root, check_layout_options=True)
    assert pipe.layout_options_report == {}
