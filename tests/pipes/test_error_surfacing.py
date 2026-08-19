# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.pipes import Pipe


class _BoomPipe(Pipe):
    async def run(self):
        raise ValueError("boom")


@pytest.mark.asyncio
async def test_pipe_error_is_surfaced_to_callback():
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
