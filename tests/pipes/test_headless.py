# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Building diagrams outside a running event loop must not raise."""

import asyncio

import pytest

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.pipes.elkjs import ElkJS


def test_schedule_run_without_event_loop_returns_none():
    pipe = Pipe()
    assert pipe.schedule_run() is None
    assert pipe._task is None


def test_diagram_with_source_builds_without_event_loop():
    # ``source=`` triggers ``_change_pipe`` -> ``refresh`` -> ``schedule_run``
    # from a trait observer during construction.
    diagram = Diagram(source=MarkElementWidget(value=Node(id="root")))
    assert diagram.refresh() is None


@pytest.mark.asyncio
async def test_headless_runner_exits_on_the_immediate_timeout(monkeypatch):
    """``IPYELK_NO_BROWSER``: no request is sent, the run fails at once and the
    runner exits -- nothing keeps re-sending across cell boundaries.
    """
    monkeypatch.setenv("IPYELK_NO_BROWSER", "true")
    elk = ElkJS(timeout=30.0)
    pipeline = Pipeline(pipes=[elk])
    pipeline.inlet.value = Node(id="root")
    sent = []
    elk.send = lambda *a, **_k: sent.append(a)
    pipeline.inlet.record(F.New)

    task = pipeline.schedule_run()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(task, timeout=1.0)
    assert sent == []
    assert pipeline._task.done()
    assert F.New in pipeline.inlet.flow, "the failed run handed its flow back"
