"""The opt-in report of layout option keys that ELK ignores (#115)."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import asyncio
import warnings
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from ipyelk.elements import Edge, Label, Node, Port
from ipyelk.pipes import MarkElementWidget, ValidationPipe
from ipyelk.pipes.valid import elk_targets
from ipyelk.schema import (
    elk_catalog,
    unknown_layout_options,
    untargeted_layout_options,
)

KNOWN = [
    "org.eclipse.elk.direction",
    "elk.direction",
    "spacing.nodeNode",
    "layered.considerModelOrder.strategy",
    "considerModelOrder.strategy",
    # an old id, and its end, that ELK still accepts for `allowNonFlowPortsToSwitchSides`
    "org.eclipse.elk.layered.northOrSouthPort",
    "northOrSouthPort",
]
UNKNOWN = [
    "org.eclipse.elk.edge.edgeNode",
    "\torg.eclipse.elk.contentAlignment",
    "elk.spacing.labelPort",
    "nodeNode.spacing",
    # ambiguous: also ends `org.eclipse.elk.layered.priority.direction`
    "direction",
    # end an id, or an old id, in the middle of a word, not after a dot
    "irection",
    "odeNode",
    "rthOrSouthPort",
]


@contextmanager
def no_user_warnings() -> Iterator[None]:
    """Turn the check's ``UserWarning`` into an error; other categories keep
    pytest's filters (the oldest environment warns about ``Comm``).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        yield


def test_catalog_is_read_once() -> None:
    assert elk_catalog() is elk_catalog()


def test_unknown_layout_options() -> None:
    assert unknown_layout_options(KNOWN) == []
    assert unknown_layout_options([*KNOWN, *UNKNOWN]) == UNKNOWN
    assert unknown_layout_options({"elk.edge.edgeNode": "10"}) == ["elk.edge.edgeNode"]


def test_untargeted_layout_options() -> None:
    keys = {
        "elk.direction": "DOWN",  # PARENTS
        "elk.nodeSize.constraints": "",  # NODES
        "elk.nodeLabels.placement": "",  # LABELS, NODES
        "elk.edge.thickness": "2",  # EDGES
        "elk.no.such.option": "",  # unknown: not a target problem
    }
    assert untargeted_layout_options(keys, ["PARENTS", "NODES"]) == [
        "elk.edge.thickness"
    ]
    assert untargeted_layout_options(keys, ["NODES"]) == [
        "elk.direction",
        "elk.edge.thickness",
    ]
    assert untargeted_layout_options(keys, ["EDGES"]) == [
        "elk.direction",
        "elk.nodeSize.constraints",
        "elk.nodeLabels.placement",
    ]


def test_elk_targets() -> None:
    leaf, port, label = Node(), Port(), Label(text="l")
    parent = Node(children=[leaf], ports=[port], labels=[label])
    root = Node(children=[parent])
    assert elk_targets(Node(), None) == ("NODES",)
    assert elk_targets(root, root) == ("PARENTS", "NODES")
    assert elk_targets(parent, root) == ("PARENTS", "NODES")
    assert elk_targets(leaf, root) == ("NODES",)
    assert elk_targets(Edge(source=leaf, target=parent), root) == ("EDGES",)
    assert elk_targets(port, root) == ("PORTS",)
    assert elk_targets(label, root) == ("LABELS",)
    assert elk_targets(object(), root) == ()


def run_pipe(
    root: Node, pipe: ValidationPipe | None = None, **kwargs
) -> ValidationPipe:
    pipe = pipe or ValidationPipe(**kwargs)
    pipe.inlet = MarkElementWidget(value=root)
    asyncio.run(pipe.run())
    return pipe


def graph() -> Node:
    root = Node(id="root", layoutOptions={"elk.direction": "DOWN", "direction": "UP"})
    label = Label(id="a.l", text="a", layoutOptions={"elk.nodeLabels.placment": "X"})
    a = Node(id="a", labels=[label], layoutOptions={"elk.nodeSize.constraints": ""})
    b = Node(id="b", layoutOptions={"elk.direction": "DOWN"})
    root.add_child(a)
    root.add_child(b)
    edge = root.add_edge(a, b)
    edge.id = "e"
    edge.layoutOptions = {"elk.nodeSize.minimum": "1"}
    return root


def test_check_is_off_by_default() -> None:
    with no_user_warnings():
        pipe = run_pipe(graph())
    assert not pipe.check_layout_options
    assert pipe.layout_options_report == {}
    assert pipe.layout_options_target_report == {}


def test_check_reports_and_warns() -> None:
    with pytest.warns(UserWarning, match="direction") as record:
        pipe = run_pipe(graph(), check_layout_options=True)
    # one warning for both reports (the oldest environment adds a `Comm` warning)
    (warning,) = (w for w in record if issubclass(w.category, UserWarning))
    assert "do not apply to their element" in str(warning.message)
    assert pipe.layout_options_report == {
        "root": ["direction"],
        "a.l": ["elk.nodeLabels.placment"],
    }
    # a parent option on a leaf node, a node option on an edge
    assert pipe.layout_options_target_report == {
        "b": ["elk.direction"],
        "e": ["elk.nodeSize.minimum"],
    }


def test_turning_the_check_off_clears_the_reports() -> None:
    with pytest.warns(UserWarning, match="layout options"):
        pipe = run_pipe(graph(), check_layout_options=True)
    assert pipe.layout_options_report
    assert pipe.layout_options_target_report
    pipe.check_layout_options = False
    assert pipe.layout_options_report == {}
    assert pipe.layout_options_target_report == {}
    with no_user_warnings():
        run_pipe(graph(), pipe)
    assert pipe.layout_options_report == {}
    assert pipe.layout_options_target_report == {}


def test_check_is_quiet_when_every_key_is_known() -> None:
    root = Node(id="root", layoutOptions={"elk.direction": "DOWN"})
    with no_user_warnings():
        pipe = run_pipe(root, check_layout_options=True)
    assert pipe.layout_options_report == {}
    assert pipe.layout_options_target_report == {}
