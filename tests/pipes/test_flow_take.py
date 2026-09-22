# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Take-at-start on the pending flow (#164, item 2).

A run *takes* ``inlet.flow`` when it starts; only a successful run consumes
what it took, and tags recorded while a run is in flight stay pending for the
next one.
"""

from __future__ import annotations

import asyncio

import pytest

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.tools import Selection, ToggleCollapsedTool, Tool


class _Parked(Pipe):
    """A pipe that waits to be released, like a browser roundtrip."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gate = asyncio.Event()
        self.runs = 0

    async def run(self):
        self.runs += 1
        await self.gate.wait()
        self.outlet.value = self.inlet.value


class _ParkedLateUnwind(_Parked):
    """Parked, and unwinding cancellation a loop turn late, as ``wait_for`` does
    on Python < 3.12 (it awaits its inner future before re-raising).
    """

    async def run(self):
        self.runs += 1
        try:
            await self.gate.wait()
        except asyncio.CancelledError:
            await asyncio.sleep(0)
            raise
        self.outlet.value = self.inlet.value


class _ParkedSwallowsCancel(_Parked):
    """Parked, but treats cancellation as "stop waiting" and completes anyway,
    a turn late; fails once released on run ``boom_on_run``.
    """

    boom_on_run: int | None = None

    async def run(self):
        self.runs = run_no = self.runs + 1
        try:
            await self.gate.wait()
        except asyncio.CancelledError:
            await asyncio.sleep(0)
        if run_no == self.boom_on_run:
            raise RuntimeError(f"boom on run {run_no}")
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


class _NoopTool(Tool):
    async def run(self):
        pass


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
    """Cancelling an in-flight run must not lose what that run took.

    A runner scheduled right after ``cancel()`` takes at its start, which can
    be before the cancelled run unwinds; ``Pipeline.cancel`` therefore hands
    the tags back first.  (``schedule_run`` itself no longer cancels: it
    joins the in-flight runner, see ``test_generation.py``.)
    """
    parked = _ParkedLateUnwind(observes=(F.New,), reports=(F.Layout,))
    counting = _Counting(observes=(F.Layout,))
    pipeline = Pipeline(pipes=[parked, counting])
    pipeline.inlet.record(F.New)

    first = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ()

    assert pipeline.cancel()
    assert pipeline.inlet.flow == (F.New,), "handed back before the successor"
    second = pipeline.schedule_run()
    assert second is not first
    with pytest.raises(asyncio.CancelledError):
        await first
    assert parked.runs == 2, "the successor started before the first unwound"

    parked.gate.set()
    await second
    await asyncio.sleep(0)

    assert parked.runs == 2, "the successor ran exactly once"
    assert counting.runs == 1, "the successor saw the flow the first run took"
    assert pipeline.inlet.flow == (), "and nothing is left spuriously pending"


@pytest.mark.asyncio
async def test_late_completing_cancelled_run_keeps_successors_taken_flow():
    """A cancelled run whose pipe swallows the cancellation completes *after*
    its successor took the flow; completing must not clear the successor's
    ``_taken``, or the successor's failure would have nothing to re-record.
    """
    parked = _ParkedSwallowsCancel(observes=(F.New,), reports=(F.Layout,))
    parked.boom_on_run = 2
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.record(F.New)

    first = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.cancel()
    second = pipeline.schedule_run()
    await first  # completes normally: the cancellation was swallowed
    assert parked.runs == 2, "the successor started before the first finished"
    assert pipeline._taken == (F.New,), "the successor's take survived"

    parked.gate.set()
    with pytest.raises(RuntimeError, match="boom on run 2"):
        await second
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == (F.New,), "re-recorded on the successor's failure"


@pytest.mark.asyncio
async def test_nested_pipeline_as_first_sub_pipe_runs():
    """The outer run took the shared inlet's flow; a nested pipeline must be
    handed that flow rather than taking ``()`` from the same inlet.
    """
    inner_first = _Counting(observes=(F.New,), reports=(F.Layout,))
    inner_second = _Counting(observes=(F.Layout,), reports=("x",))
    outer = Pipeline(
        pipes=[
            Pipeline(pipes=[inner_first]),
            Pipeline(pipes=[inner_second]),
        ]
    )
    outer.inlet.record(F.New)

    await outer.run()

    assert inner_first.runs == 1
    assert inner_second.runs == 1
    assert outer.inlet.flow == ()
    assert outer.status.exception is None


@pytest.mark.asyncio
async def test_two_tool_handlers_recording_mid_run_both_survive():
    """``Tool.handler`` records: a second tool's report does not overwrite the
    first's, and neither is erased by the in-flight run's completion.
    """
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.record(F.New)
    tool_a = _NoopTool(reports=("a",), tee=pipeline)
    tool_b = _NoopTool(reports=("b",), tee=pipeline)

    run = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ()

    await tool_a.handler()
    await tool_b.handler()
    assert pipeline.inlet.flow == ("a", "b")

    parked.gate.set()
    await run
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ("a", "b")


@pytest.mark.asyncio
async def test_toggle_collapsed_records_alongside_another_tool():
    """``ToggleCollapsedTool.run`` records too: its ``hidden`` report and a
    concurrent tool's report both survive the parked run.
    """
    root = Node(id="root", children=[Node(id="a", children=[Node(id="c")])])
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.value = root
    pipeline.inlet.build_index()
    pipeline.inlet.record(F.New)
    selection = Selection(tee=pipeline, ids=("a",))
    toggle = ToggleCollapsedTool(selection=selection, tee=pipeline)
    other = _NoopTool(reports=("r",), tee=pipeline)

    run = pipeline.schedule_run()
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ()

    await other.handler()
    await toggle.run()
    assert pipeline.inlet.flow == ("r", F.Node.hidden)
    assert root.children[0].children[0].properties.hidden is True

    parked.gate.set()
    await run
    await asyncio.sleep(0)
    assert pipeline.inlet.flow == ("r", F.Node.hidden)


def test_update_view_sources_merges_pending_tag():
    """``Diagram._update_view_sources`` records ``New`` next to what a caller
    already left pending on the source, instead of overwriting it.
    """
    source = MarkElementWidget(value=Node(id="root"))
    source.record("r")
    diagram = Diagram(source=source, pipe=Pipeline(pipes=[Pipe()]))
    assert diagram.source is source
    assert diagram.source.flow == ("r", F.New)


@pytest.mark.asyncio
async def test_standalone_pipe_check_dirty_reads_inlet_flow():
    """Outside a pipeline ``check_dirty()`` is unchanged: it reads ``inlet.flow``."""
    pipe = Pipe(observes=("a",), reports=("b",))
    pipe.inlet.record("a")
    assert pipe.check_dirty()
    assert pipe.inlet.flow == ("a",), "a bare pipe does not consume the flow"
    assert not pipe.check_dirty(())
