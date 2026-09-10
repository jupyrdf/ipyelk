# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio

import pytest

from ipyelk.pipes import Pipe
from ipyelk.pipes.pipeline import Pipeline
from ipyelk.tools import PipelineProgressBar


class _BoomPipe(Pipe):
    async def run(self):
        raise RuntimeError("Id must be a string or an integer: null")


@pytest.mark.asyncio
async def test_layout_error_finishes_the_progress_bar():
    """A failed run must surface its own error and reach a terminal bar state.

    The progress callback runs inside the pipeline's error handling: it must
    not clobber the surfaced exception (`PipeStatus.step()` returned `None`
    for errored pipes, so `get_progress_value()` raised `TypeError` mid
    `except` -- `on_error` saw the `TypeError` and the bar sat "in progress"
    forever).
    """
    bar_tool = PipelineProgressBar()
    pipeline = Pipeline(
        pipes=[_BoomPipe(observes=("layout",), reports=("anythinglayout",))],
        on_progress=bar_tool.update,
    )
    seen = []
    pipeline.on_error = lambda _pipe, exc: seen.append(exc)
    pipeline.inlet.flow = ("layout",)

    task = pipeline.schedule_run()
    with pytest.raises(RuntimeError, match="Id must be a string"):
        await task
    await asyncio.sleep(0)

    assert [type(exc) for exc in seen] == [RuntimeError]
    assert isinstance(pipeline.status.exception, RuntimeError)

    bar = bar_tool.bar
    assert bar.value == bar.max
    assert bar.bar_style == "warning"
    assert bar.layout.visibility == "visible"


@pytest.mark.asyncio
async def test_clean_run_hides_the_progress_bar():
    bar_tool = PipelineProgressBar()
    pipeline = Pipeline(pipes=[Pipe()], on_progress=bar_tool.update)

    await pipeline.schedule_run()
    await asyncio.sleep(0)

    bar = bar_tool.bar
    assert bar.value == bar.max
    assert not bar.bar_style
    assert bar.layout.visibility == "hidden"


@pytest.mark.asyncio
async def test_terminal_state_echoes_are_scheduled_cancelled_and_bounded():
    """The terminal bar update is re-sent later; a new run or close cancels it.

    Kernel unit check only: it drives the scheduled callbacks directly and
    does not model a lossy channel or a browser.
    """
    bar_tool = PipelineProgressBar()
    pipeline = Pipeline(pipes=[Pipe()], on_progress=bar_tool.update)
    bar = bar_tool.bar
    sent = []
    bar.send_state = lambda *_a, **_k: sent.append("bar")
    bar.layout.send_state = lambda *_a, **_k: sent.append("layout")

    await pipeline.schedule_run()
    await asyncio.sleep(0)
    assert bar.value == bar.max
    handles = bar_tool._echo_handles
    assert len(handles) == len(bar_tool.echo_delays) == 2
    assert not any(h.cancelled() for h in handles)

    # the echo re-sends the (still terminal) state ...
    sent.clear()  # trait changes during update() also send_state(key=...)
    bar_tool._echo_terminal_state()
    assert sent == ["bar", "layout"]

    # ... but not once a new run has reset the bar (pipeline progress is the
    # mean of its pipes' progress)
    pipeline.pipes[0].status = pipeline.status.running()
    bar_tool.update(pipeline)
    assert bar.value < bar.max
    assert all(h.cancelled() for h in handles)
    assert bar_tool._echo_handles == ()
    sent.clear()
    bar_tool._echo_terminal_state()
    assert sent == []

    # close cancels whatever is pending
    await pipeline.schedule_run()
    await asyncio.sleep(0)
    handles = bar_tool._echo_handles
    assert handles
    bar_tool.close()
    assert all(h.cancelled() for h in handles)
