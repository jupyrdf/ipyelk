# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Generation counter and coalescing (#164, item 3).

``schedule_run`` never cancels: one runner serves every request made while it
is alive (trailing edge), a ``Pipeline`` gives way to a newer request only
between stages, and a browser roundtrip that was sent is awaited to its
answer.  Answers carry the request's generation so a stale one is dropped.
"""

from __future__ import annotations

import asyncio
import logging

import pytest

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.pipes.elkjs import ElkJS


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


class _Counting(Pipe):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runs = 0

    async def run(self):
        self.runs += 1
        self.outlet.value = self.inlet.value


class _Flaky(Pipe):
    """Fails on its first run only."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runs = 0

    async def run(self):
        self.runs += 1
        await asyncio.sleep(0)
        if self.runs == 1:
            raise RuntimeError("transient")
        self.outlet.value = self.inlet.value


def _elkjs(node_id="root") -> tuple[ElkJS, list]:
    pipe = ElkJS(timeout=5.0)
    pipe.inlet = MarkElementWidget(value=Node(id=node_id))
    pipe.outlet = MarkElementWidget()
    sends: list = []
    pipe.send = lambda content, *_a, **_k: sends.append(content)
    return pipe, sends


def _answer(pipe, gen: int, node_id: str = "laid-out") -> None:
    """The browser's write: ``value`` and ``gen`` in one ``set_state``."""
    pipe.outlet.set_state({"value": {"id": node_id}, "gen": gen})


async def _ticks(n: int = 3) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_ten_refreshes_one_run(monkeypatch):
    """Ten ``refresh()`` in one tick: one ``run`` message, one view update."""
    updates = []
    original = Diagram._update_view
    monkeypatch.setattr(
        Diagram,
        "_update_view",
        lambda self, fut: (updates.append(fut), original(self, fut)),
    )
    elk, sends = _elkjs()
    diagram = Diagram(
        source=MarkElementWidget(value=Node(id="root")), pipe=Pipeline(pipes=[elk])
    )
    # answer whatever generation is asked, one tick later
    loop = asyncio.get_running_loop()
    elk.send = lambda content, *_a, **_k: (
        sends.append(content),
        loop.call_soon(_answer, elk, content["gen"]),
    )
    await diagram.pipe._task  # construction's own refresh
    await _ticks()
    sends.clear()
    updates.clear()

    diagram.pipe.inlet.record(F.New)
    tasks = [diagram.refresh() for _ in range(10)]
    assert len({id(t) for t in tasks}) == 1, "one runner serves the burst"
    await tasks[0]
    await _ticks()

    assert sends == [{"action": "run", "gen": 2}]
    assert len(updates) == 1
    assert not any(t.cancelled() for t in tasks)


@pytest.mark.asyncio
async def test_stale_answer_is_dropped():
    """An answer for an older generation leaves the wait pending."""
    pipe, sends = _elkjs()
    run1 = asyncio.create_task(pipe.run())
    await _ticks()
    assert sends == [{"action": "run", "gen": 1}]
    _answer(pipe, 1, "first")
    await run1
    assert pipe.outlet.value.id == "first"

    run2 = asyncio.create_task(pipe.run())
    await _ticks()
    assert sends[-1] == {"action": "run", "gen": 2}
    _answer(pipe, 1, "late-for-gen-1")  # the browser finishing old work
    await _ticks()
    assert not run2.done(), "an older generation does not answer this run"
    assert pipe._roundtrip_future is not None
    assert not pipe._roundtrip_future.done()

    _answer(pipe, 2, "second")
    await asyncio.wait_for(run2, timeout=2.0)
    assert pipe.outlet.value.id == "second"
    assert pipe.outlet.gen == 2


@pytest.mark.asyncio
async def test_in_flight_roundtrip_is_not_cancelled():
    """Scheduling during a roundtrip: run 1 consumes its answer, run 2 follows."""
    elk, sends = _elkjs("v1")
    pipeline = Pipeline(pipes=[elk])
    pipeline.inlet.record(F.New)

    first = pipeline.schedule_run()
    await _ticks()
    assert [s["gen"] for s in sends] == [1]

    pipeline.inlet.value = Node(id="v2")
    pipeline.inlet.record(F.New)
    second = pipeline.schedule_run()
    assert second is first, "the in-flight runner serves the new request"
    await _ticks()
    assert not first.cancelled()
    assert [s["gen"] for s in sends] == [1], "no second request while one is out"

    _answer(elk, 1, "answer-for-v1")
    await _ticks()
    assert elk.outlet.value.id == "answer-for-v1", "consumed by run 1"
    assert [s["gen"] for s in sends] == [1, 2], "run 2 starts after run 1 answers"
    assert not first.done()

    _answer(elk, 2, "answer-for-v2")
    await asyncio.wait_for(first, timeout=2.0)
    assert elk.outlet.value.id == "answer-for-v2"
    assert pipeline.inlet.flow == ()


@pytest.mark.asyncio
async def test_supersede_between_stages_re_records_flow():
    """A request made mid-run aborts at the next stage boundary; the taken
    flow is handed back and the newer run takes it.
    """
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    counting = _Counting(observes=(F.Layout,), reports=("x",))
    pipeline = Pipeline(pipes=[parked, counting])
    pipeline.inlet.record(F.New)

    task = pipeline.schedule_run()
    await _ticks()
    assert parked.runs == 1
    assert pipeline.inlet.flow == ()

    assert pipeline.schedule_run() is task  # a newer request, stage 0 in flight
    parked.gate.set()  # stage 0 completes; stage 1 must not start on stale work
    await asyncio.wait_for(task, timeout=2.0)

    assert parked.runs == 2, "the newer run re-ran stage 0 with the re-recorded flow"
    assert counting.runs == 1, "stage 1 ran once, for the newer run only"
    assert pipeline.inlet.flow == ()
    assert not task.cancelled()
    assert pipeline.status.exception is None


@pytest.mark.asyncio
async def test_cancel_is_explicit():
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.record(F.New)

    task = pipeline.schedule_run()
    assert pipeline.schedule_run() is task, "schedule_run never cancels"
    await _ticks()
    assert pipeline.inlet.flow == ()

    assert pipeline.cancel() is True
    assert pipeline.inlet.flow == (F.New,), "the taken flow is handed back"
    assert pipeline.cancel() is False
    with pytest.raises(asyncio.CancelledError):
        await task

    parked.gate.set()
    successor = pipeline.schedule_run()
    assert successor is not task
    await asyncio.wait_for(successor, timeout=2.0)
    assert parked.runs == 2
    assert pipeline.inlet.flow == ()


@pytest.mark.asyncio
async def test_cancel_mid_roundtrip_ignores_the_late_answer():
    pipe, sends = _elkjs()
    task = pipe.schedule_run()
    await _ticks()
    assert pipe.cancel()
    await _ticks()
    assert task.cancelled()
    assert pipe._roundtrip_future is None

    successor = pipe.schedule_run()
    await _ticks()
    assert [s["gen"] for s in sends] == [1, 2]
    _answer(pipe, 1, "late")
    await _ticks()
    assert not successor.done()
    _answer(pipe, 2, "fresh")
    await asyncio.wait_for(successor, timeout=2.0)
    assert pipe.outlet.value.id == "fresh"


@pytest.mark.asyncio
async def test_old_frontend_gen_zero_accepted_once_warned_per_pipe(caplog):
    """A frontend build that writes only ``value`` is accepted, warned once per
    pipe: each diagram that meets such a frontend says so, one time.
    """
    for expected_warnings in (1, 2):
        pipe, _sends = _elkjs()
        assert pipe._warned_unversioned is False
        for _ in range(2):
            task = asyncio.create_task(pipe.run())
            await _ticks()
            with caplog.at_level(logging.WARNING, logger="traitlets"):
                # the browser's write, without a gen
                pipe.outlet.set_state({"value": {"id": "unversioned"}})
                await asyncio.wait_for(task, timeout=2.0)
        assert pipe.outlet.gen == 0
        assert pipe._warned_unversioned is True
        warnings = [
            r for r in caplog.records if "without a generation" in r.getMessage()
        ]
        assert len(warnings) == expected_warnings


@pytest.mark.asyncio
async def test_failed_run_with_pending_request_serves_the_newer_one():
    """The runner does not drop a request because the previous run failed."""
    flaky = _Flaky()
    task = flaky.schedule_run()
    await asyncio.sleep(0)
    assert flaky.schedule_run() is task
    await asyncio.wait_for(task, timeout=2.0)
    assert flaky.runs == 2
    assert task.exception() is None

    boom = _Flaky()
    with pytest.raises(RuntimeError, match="transient"):
        await boom.schedule_run()
    assert boom.runs == 1, "nothing pending: the failure propagates"


@pytest.mark.asyncio
async def test_refresh_inside_update_view_starts_a_new_runner(monkeypatch):
    counting = _Counting(observes=(F.New,), reports=(F.Layout,))
    diagram = Diagram(
        source=MarkElementWidget(value=Node(id="root")),
        pipe=Pipeline(pipes=[counting]),
    )
    first = diagram.pipe._task
    await first
    await _ticks()
    runners = []
    original = Diagram._update_view

    def update_view(self, future):
        original(self, future)
        runners.append(self.pipe._task)
        if len(runners) == 1:
            self.pipe.inlet.record(F.New)
            self.refresh()

    monkeypatch.setattr(Diagram, "_update_view", update_view)
    diagram.pipe.inlet.record(F.New)
    second = diagram.refresh()
    assert second is not first
    await second
    await _ticks()
    assert len(runners) == 2
    assert runners[1] is not second
    await runners[1]
    assert counting.runs == 3


@pytest.mark.asyncio
async def test_replacing_the_source_cancels_the_detached_run():
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    diagram = Diagram(
        source=MarkElementWidget(value=Node(id="a")), pipe=Pipeline(pipes=[parked])
    )
    detached = diagram.pipe._task
    old_source = diagram.source
    await _ticks()
    assert old_source.flow == ()

    diagram.source = MarkElementWidget(value=Node(id="b"))
    assert old_source.flow == (F.New,), "handed back to the old source"
    with pytest.raises(asyncio.CancelledError):
        await detached
    parked.gate.set()
    await asyncio.wait_for(diagram.pipe._task, timeout=2.0)
    assert diagram.pipe.inlet is diagram.source
    assert diagram.source.flow == ()


@pytest.mark.asyncio
async def test_identical_answer_arriving_as_gen_alone_resolves():
    """The browser's update is a Backbone diff: a layout deep-equal to the
    previous answer arrives as a change of ``gen`` only (an older extension
    build; the current one forces ``value`` in).  The roundtrip must still
    resolve instead of waiting out its deadline.
    """
    pipe, sends = _elkjs()
    run1 = asyncio.create_task(pipe.run())
    await _ticks()
    _answer(pipe, 1, "same")
    await asyncio.wait_for(run1, timeout=2.0)

    run2 = asyncio.create_task(pipe.run())
    await _ticks()
    assert sends[-1] == {"action": "run", "gen": 2}
    pipe.outlet.set_state({"gen": 2})  # `value` dropped from the diff
    await asyncio.wait_for(run2, timeout=2.0)
    assert pipe.outlet.value.id == "same"
    assert pipe.outlet.gen == 2
    assert pipe._roundtrip_future is None


@pytest.mark.asyncio
async def test_kernel_write_during_first_roundtrip_is_not_an_answer(caplog):
    """While ``outlet.gen`` is still 0 a kernel-side ``value`` write must not
    pass for the browser's (unversioned) answer; a browser ``set_state``
    without ``gen`` still does, with one warning.
    """
    pipe, _sends = _elkjs()
    task = asyncio.create_task(pipe.run())
    await _ticks()
    with caplog.at_level(logging.WARNING, logger="traitlets"):
        pipe.outlet.value = Node(id="kernel-side")
        await _ticks()
        assert not task.done(), "a kernel write is not the browser's answer"
        assert pipe.outlet.gen == 0
        assert not [r for r in caplog.records if "without a generation" in r.msg]

        pipe.outlet.set_state({"value": {"id": "from-browser"}})  # no gen
        await asyncio.wait_for(task, timeout=2.0)
    assert pipe.outlet.value.id == "from-browser"
    warnings = [r for r in caplog.records if "without a generation" in r.getMessage()]
    assert len(warnings) == 1


def _error(pipe, gen: int | None, text: str = "elk exploded") -> None:
    content = {"action": "error", "error": text}
    if gen is not None:
        content["gen"] = gen
    pipe._handle_browser_msg(pipe, content, None)


@pytest.mark.asyncio
async def test_late_error_for_an_abandoned_generation_is_ignored():
    """The browser reports a failed run with its generation; only the pending
    generation's error rejects the roundtrip.
    """
    pipe, sends = _elkjs()
    task = pipe.schedule_run()
    await _ticks()
    assert pipe.cancel()
    await _ticks()
    assert task.cancelled()

    successor = pipe.schedule_run()
    await _ticks()
    assert [s["gen"] for s in sends] == [1, 2]
    _error(pipe, 1, "late failure of the abandoned run")
    await _ticks()
    assert not successor.done(), "an error for generation 1 is not ours"
    assert not pipe._roundtrip_future.done()

    _error(pipe, 2)
    with pytest.raises(RuntimeError, match="elk exploded"):
        await asyncio.wait_for(successor, timeout=2.0)


@pytest.mark.asyncio
async def test_error_without_a_generation_rejects_the_pending_roundtrip():
    """An older extension build reports errors unstamped: still fatal."""
    pipe, _sends = _elkjs()
    task = asyncio.create_task(pipe.run())
    await _ticks()
    _error(pipe, None)
    with pytest.raises(RuntimeError, match="elk exploded"):
        await asyncio.wait_for(task, timeout=2.0)
    assert pipe._roundtrip_future is None
    _error(pipe, None)  # nothing pending: harmless


class _Reentrant(Pipe):
    """Requests itself once more from inside ``run``, without ever awaiting."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runs = 0

    async def run(self):
        self.runs += 1
        if self.runs == 1:
            self.schedule_run()
        self.outlet.value = self.inlet.value


@pytest.mark.asyncio
async def test_runner_yields_between_runs():
    """A run that never awaits and requests again from inside must not spin
    the runner synchronously: the loop turns between runs.
    """
    pipe = _Reentrant()
    task = pipe.schedule_run()
    seen: list[int] = []

    async def watcher():
        while not task.done():
            seen.append(pipe.runs)
            await asyncio.sleep(0)

    watching = asyncio.create_task(watcher())
    await asyncio.wait_for(task, timeout=2.0)
    await watching

    assert pipe.runs == 2
    assert 1 in seen, "the loop turned between the two runs"


@pytest.mark.asyncio
async def test_late_unwinding_cancelled_roundtrip_keeps_successors_future(
    monkeypatch,
):
    """``cancel()`` plus ``schedule_run()`` in one tick (what ``Diagram`` does
    on ``source`` replacement): when the cancelled roundtrip unwinds a turn
    late (``wait_for`` on Python < 3.12), its cleanup must not null the
    future the successor is already waiting on, or a browser error for the
    successor's generation finds nothing to reject.
    """
    original = asyncio.wait_for

    async def late_wait_for(aw, timeout):
        try:
            return await original(aw, timeout)
        except asyncio.CancelledError:
            await asyncio.sleep(0)
            raise

    monkeypatch.setattr(asyncio, "wait_for", late_wait_for)
    pipe, sends = _elkjs()
    first = pipe.schedule_run()
    await _ticks()
    assert pipe._roundtrip_future is not None

    assert pipe.cancel()
    successor = pipe.schedule_run()
    await _ticks()
    assert first.cancelled()
    assert [s["gen"] for s in sends] == [1, 2]
    future = pipe._roundtrip_future
    assert future is not None, "the successor's future survived"
    assert not future.done()

    _error(pipe, 2)
    with pytest.raises(RuntimeError, match="elk exploded"):
        await original(successor, 2.0)
    assert pipe._roundtrip_future is None
