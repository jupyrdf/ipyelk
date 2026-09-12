# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Building diagrams outside a running event loop must not raise."""

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe


def test_schedule_run_without_event_loop_returns_none():
    pipe = Pipe()
    assert pipe.schedule_run() is None
    assert pipe._task is None


def test_diagram_with_source_builds_without_event_loop():
    # ``source=`` triggers ``_change_pipe`` -> ``refresh`` -> ``schedule_run``
    # from a trait observer during construction.
    diagram = Diagram(source=MarkElementWidget(value=Node(id="root")))
    assert diagram.refresh() is None
