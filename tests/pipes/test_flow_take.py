# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Take-at-start on the pending flow (#164, item 2).

A run *takes* ``inlet.flow`` when it starts; only a successful run consumes
what it took, and tags recorded while a run is in flight stay pending for the
next one.
"""

import asyncio

import pytest

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.tools import Tool


class _Parked(Pipe):
    """A pipe that waits to be released, like a browser roundtrip."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gate = asyncio.Event()

    async def run(self):
        await self.gate.wait()
        self.outlet.value = self.inlet.value


class _Counting(Pipe):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runs = 0

    async def run(self):
        self.runs += 1
        self.outlet.value = self.inlet.value


class _Boom(Pipe):
    async def run(self):
        raise RuntimeError("boom")


class _BoomTool(Tool):
    async def run(self):
        raise RuntimeError("half done")


def test_take_is_atomic():
    inlet = MarkElementWidget(flow=("a", "b"))
    assert inlet.take() == ("a", "b")
    assert inlet.flow == ()
    assert inlet.take() == ()


def test_record_merges():
    inlet = MarkElementWidget()
    inlet.record("a")
    inlet.record("b", "a")
    assert inlet.flow == ("a", "b")
    inlet.record("a")
    assert inlet.flow == ("a", "b"), "a duplicate is not appended"
    inlet.record()
    assert inlet.flow == ("a", "b")


@pytest.mark.asyncio
async def test_failed_tool_reports_survive_next_completion():
    """The p2 scenario: a tool records ``r`` and fails while a run is parked.

    Completing the parked run used to assign ``flow = ()`` and wipe ``r``.
    """
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked, Pipe(observes=("r",), reports=("r2",))])
    diagram = Diagram(
        source=MarkElementWidget(value=Node(id="root")),
        pipe=pipeline,
        tools=[_BoomTool(reports=("r",))],
    )
    run = diagram.pipe._task
    assert run is not None, "construction schedules a refresh"
    await asyncio.sleep(0)  # the run starts and takes ``("new",)``
    assert diagram.pipe.inlet.flow == ()

    tool_task = diagram.tools[0].handler()
    assert "r" in diagram.pipe.inlet.flow
    with pytest.raises(RuntimeError, match="half done"):
        await tool_task

    parked.gate.set()
    await run
    for _ in range(3):
        await asyncio.sleep(0)  # ``Diagram.refresh``'s done-callback

    assert "r" in diagram.pipe.inlet.flow
    assert diagram.pipe.check_dirty()


@pytest.mark.asyncio
async def test_failed_run_re_records_taken_flow():
    """A pipe raising at stage 2 hands the taken flow back so a retry sees it."""
    first = _Counting(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[first, _Boom(observes=(F.Layout,))])
    pipeline.inlet.record(F.New)

    with pytest.raises(RuntimeError, match="boom"):
        await pipeline.run()

    assert F.New in pipeline.inlet.flow
    assert first.runs == 1

    # ... and the same through the scheduler / done-callback path
    task = pipeline.schedule_run()
    with pytest.raises(RuntimeError, match="boom"):
        await task
    await asyncio.sleep(0)
    assert F.New in pipeline.inlet.flow
    assert first.runs == 2


@pytest.mark.asyncio
async def test_report_recorded_during_run_is_kept_for_next_run():
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    on_hidden = _Counting(observes=(F.AnyHidden,), reports=("x",))
    pipeline = Pipeline(pipes=[parked, on_hidden])
    pipeline.inlet.record(F.New)

    task = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == (), "the run took the flow when it started"

    pipeline.inlet.record(F.Node.hidden)  # a tool reports mid-run
    parked.gate.set()
    await task
    await asyncio.sleep(0)

    assert pipeline.inlet.flow == (F.Node.hidden,), "not erased by completion"
    assert on_hidden.runs == 0

    await pipeline.run()
    assert on_hidden.runs == 1
    assert pipeline.inlet.flow == ()


@pytest.mark.asyncio
async def test_cancelled_run_hands_taken_flow_to_successor():
    """Rescheduling over an in-flight run must not lose what that run took.

    The successor takes at its start, which can be before the cancelled run
    unwinds; ``Pipeline.schedule_run`` therefore hands the tags back first.
    """
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    counting = _Counting(observes=(F.Layout,))
    pipeline = Pipeline(pipes=[parked, counting])
    pipeline.inlet.record(F.New)

    first = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ()

    second = pipeline.schedule_run()
    assert second is not first
    with pytest.raises(asyncio.CancelledError):
        await first

    parked.gate.set()
    await second
    await asyncio.sleep(0)

    assert counting.runs == 1, "the successor saw the flow the first run took"
    assert pipeline.inlet.flow == (), "and nothing is left spuriously pending"


@pytest.mark.asyncio
async def test_standalone_pipe_check_dirty_reads_inlet_flow():
    """Outside a pipeline ``check_dirty()`` is unchanged: it reads ``inlet.flow``."""
    pipe = Pipe(observes=("a",), reports=("b",))
    pipe.inlet.record("a")
    assert pipe.check_dirty()
    assert pipe.inlet.flow == ("a",), "a bare pipe does not consume the flow"
    assert not pipe.check_dirty(())
