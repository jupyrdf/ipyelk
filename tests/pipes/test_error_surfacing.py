# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
import logging

import pytest

from ipyelk.exceptions import ClosedError
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.pipes.base import PipeStatus


class _BoomPipe(Pipe):
    async def run(self):
        raise ValueError("boom")


@pytest.mark.asyncio
async def test_pipe_error_is_surfaced_to_callback():
    """Errors raised by async pipe tasks are passed to the error callback."""
    pipe = _BoomPipe()
    seen = []
    pipe.on_error = lambda p, exc: seen.append((p, exc))

    task = pipe.schedule_run()
    with pytest.raises(ValueError, match="boom"):
        await task

    # Let the done-callback run.
    await asyncio.sleep(0)

    assert len(seen) == 1
    surfaced_pipe, surfaced_exc = seen[0]
    assert surfaced_pipe is pipe
    assert isinstance(surfaced_exc, ValueError)
    assert pipe.status.exception is surfaced_exc


@pytest.mark.asyncio
async def test_pipe_cancellation_does_not_trigger_on_error():
    pipe = _BoomPipe()
    seen = []
    pipe.on_error = lambda p, exc: seen.append((p, exc))

    task = pipe.schedule_run()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)

    assert seen == []


class _CloseThenBoom(Pipe):
    hook = None
    error_type = ValueError

    async def run(self):
        self.hook()
        raise self.error_type("boom after close")


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [ValueError, ClosedError])
async def test_stage_error_after_close_is_cancellation(caplog, error_type):
    source = MarkElementWidget(flow=(F.New,))
    stage = _CloseThenBoom(observes=(F.New,))
    pipeline = Pipeline(inlet=source, pipes=[stage])
    stage.hook = pipeline.close
    stage.error_type = error_type
    seen = []
    pipeline.on_error = lambda pipe, exc: seen.append((pipe, exc))

    try:
        task = pipeline.schedule_run()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

        assert task.cancelled()
        assert source.flow == (F.New,)
        assert seen == []
        assert pipeline.status.exception is None
        assert stage.status.exception is None
        assert caplog.records == []
    finally:
        pipeline.close()
        source.close()


@pytest.mark.asyncio
async def test_close_in_the_run_entry_window_is_cancellation(caplog, monkeypatch):
    """A close between the runner's own check and ``Pipeline.run``'s guard."""
    pipeline = Pipeline(pipes=[Pipe(observes=(F.New,), reports=(F.Layout,))])
    seen = []
    pipeline.on_error = lambda pipe, exc: seen.append((pipe, exc))
    pipeline.inlet.record(F.New)
    run = pipeline.run

    async def close_then_run(flow=None):
        pipeline.close()
        await run(flow)

    monkeypatch.setattr(pipeline, "run", close_then_run)
    try:
        task = pipeline.schedule_run()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

        assert task.cancelled()
        assert pipeline.inlet.flow == (F.New,)
        assert seen == []
        assert caplog.records == []
    finally:
        pipeline.close()


class _PokeClosedThenRequest(Pipe):
    """A stage that requests a newer run, then trips over another closed pipe."""

    other = None
    owner = None
    calls = 0

    async def run(self):
        self.calls += 1
        if self.calls == 1:
            self.owner.schedule_run()
            self.other.schedule_run()


@pytest.mark.asyncio
async def test_superseded_run_failing_with_a_foreign_closed_error_serves_newer(
    caplog,
):
    """A ``ClosedError`` about another pipe is an ordinary failure: with a newer
    request pending it is logged and the newer request is served.
    """
    other = Pipeline()
    other.close()
    source = MarkElementWidget(flow=(F.New,))
    stage = _PokeClosedThenRequest(observes=(F.New,))
    pipeline = Pipeline(inlet=source, pipes=[stage])
    stage.other, stage.owner = other, pipeline
    seen = []
    pipeline.on_error = lambda pipe, exc: seen.append((pipe, exc))

    try:
        task = pipeline.schedule_run()
        await task
        await asyncio.sleep(0)

        assert stage.calls == 2, "the newer request was not served"
        assert seen == []
        assert not pipeline.closed
        warnings = [
            r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert warnings == ["Pipeline run failed; serving the newer request"]
    finally:
        pipeline.close()
        source.close()


@pytest.mark.asyncio
async def test_queued_close_before_error_callback_keeps_flow_and_skips_callback(
    caplog,
):
    source = MarkElementWidget(flow=(F.New,))
    stage = _CloseThenBoom(observes=(F.New,))
    pipeline = Pipeline(inlet=source, pipes=[stage])
    stage.hook = lambda: asyncio.get_running_loop().call_soon(pipeline.close)
    seen = []
    updates_after_close = []
    pipeline.on_error = lambda pipe, exc: seen.append((pipe, exc))
    pipeline.observe(
        lambda change: (
            updates_after_close.append(change.new) if pipeline.closed else None
        ),
        "status",
    )

    try:
        task = pipeline.schedule_run()
        with pytest.raises(ValueError, match="boom after close"):
            await task
        await asyncio.sleep(0)

        assert pipeline.closed
        assert source.flow == (F.New,)
        assert seen == []
        assert updates_after_close == []
        warnings = [
            r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert warnings == [
            "Pipeline was closed before its run failed with ValueError('boom after close')"
        ]
    finally:
        pipeline.close()
        source.close()


class _TrackedFuture(asyncio.Future):
    retrieved = False

    def exception(self):
        self.retrieved = True
        return super().exception()


@pytest.mark.asyncio
@pytest.mark.parametrize("pipe_type", [Pipe, Pipeline])
async def test_closed_pipe_consumes_error_without_reporting_it(pipe_type, caplog):
    pipe = pipe_type()
    seen = []
    pipe.on_error = lambda pipe, exc: seen.append((pipe, exc))
    pipe.close()
    status = pipe.status
    failed = _TrackedFuture()
    failed.set_exception(ValueError("completed before close"))

    pipe._post_run(failed)

    assert failed.retrieved
    assert seen == []
    assert pipe.status is status
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    expected = f"{pipe_type.__name__} was closed before its run failed with "
    assert warnings == [expected + "ValueError('completed before close')"]


def test_status_observer_close_suppresses_progress_callback():
    pipe = Pipe()
    progress = []
    updates = []
    pipe.observe(lambda change: (updates.append(change.new), pipe.close()), "status")
    pipe.on_progress = progress.append

    pipe.status_update(PipeStatus.running())
    pipe.status_update(PipeStatus.finished())

    assert pipe.status.state() == "cancelled"
    assert len(updates) == 1
    assert progress == []
