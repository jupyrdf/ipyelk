# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F


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

    async def run(self):
        self.hook()
        raise ValueError("boom after close")


@pytest.mark.asyncio
async def test_stage_error_after_close_is_cancellation(caplog):
    source = MarkElementWidget(flow=(F.New,))
    stage = _CloseThenBoom(observes=(F.New,))
    pipeline = Pipeline(inlet=source, pipes=[stage])
    stage.hook = pipeline.close
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
async def test_queued_close_before_error_callback_keeps_flow_and_skips_callback():
    source = MarkElementWidget(flow=(F.New,))
    stage = _CloseThenBoom(observes=(F.New,))
    pipeline = Pipeline(inlet=source, pipes=[stage])
    stage.hook = lambda: asyncio.get_running_loop().call_soon(pipeline.close)
    seen = []
    updates_after_close = []
    pipeline.on_error = lambda pipe, exc: seen.append((pipe, exc))
    pipeline.observe(
        lambda change: (
            updates_after_close.append(change.new) if pipeline._closed else None
        ),
        "status",
    )

    try:
        task = pipeline.schedule_run()
        with pytest.raises(ValueError, match="boom after close"):
            await task
        await asyncio.sleep(0)

        assert pipeline._closed
        assert source.flow == (F.New,)
        assert seen == []
        assert updates_after_close == []
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
async def test_closed_pipe_consumes_error_without_reporting_it(pipe_type):
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
