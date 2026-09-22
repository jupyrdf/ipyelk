# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Runners and browser answers on different event loops (#164).

With ipykernel >= 7 and a frontend that uses kernel subshells (JupyterLab
4.5+, ipywidgets 8.1.8+), cells run on the kernel's main loop while every
widget message -- the browser's answer to a ``run`` request, a button click --
is handled on a *subshell* thread with its own loop.  Two things must then
hold, neither of which needs a browser to check:

* an answer written from the subshell thread settles the roundtrip future on
  the runner's own loop and wakes it (``util.settle``), instead of leaving the
  runner to notice at its next re-send timer;
* ``schedule_run`` called from the subshell loop while a runner from a cell is
  alive hands over to a runner on the caller's loop -- one it can await --
  cancelling the old one and keeping its pending request and taken flow.

The "subshell" here is a plain thread running its own event loop; the pytest
loop plays the kernel's main loop.
"""

from __future__ import annotations

import asyncio
import threading
from time import monotonic

import pytest

from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline
from ipyelk.pipes import flows as F
from ipyelk.pipes.elkjs import ElkJS

#: well under ``browser_roundtrip``'s first re-send (0.5 s): an answer that
#: only lands when that timer wakes the loop fails this bound
PROMPT = 0.25


@pytest.fixture
def subshell():
    """A second thread running its own event loop, like a kernel subshell."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, name="subshell", daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=5)
    loop.close()


async def _on(loop: asyncio.AbstractEventLoop, coro):
    """Run ``coro`` on ``loop`` (another thread) and await its outcome here."""
    return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop))


async def _ticks(n: int = 5) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class _Parked(Pipe):
    """A pipe that waits to be released, like a browser roundtrip.

    Each run parks on a future of its own loop (an ``asyncio.Event`` binds to
    one loop and rejects the other) and sets no timer: a loop nobody wakes
    must stay asleep, or the tests below could not tell a delivered answer or
    cancel from one that merely waited for the next timer.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.runs = 0
        self.loops: list[asyncio.AbstractEventLoop] = []
        self.gates: list[asyncio.Future] = []

    async def run(self):
        self.runs += 1
        loop = asyncio.get_running_loop()
        self.loops.append(loop)
        gate = loop.create_future()
        self.gates.append(gate)
        await gate
        self.outlet.value = self.inlet.value

    def release(self) -> None:
        """Let every parked run go, from any thread."""
        for gate in self.gates:
            gate.get_loop().call_soon_threadsafe(
                lambda g=gate: g.done() or g.set_result(None)
            )


@pytest.mark.asyncio
async def test_answer_from_another_thread_wakes_the_runner(subshell):
    """The browser's ``set_state`` arrives on the subshell thread; the runner
    on the main loop must resolve promptly, not at the 0.5 s re-send timer,
    and must not re-send the request it already has an answer for.
    """
    pipe = ElkJS(timeout=5.0)
    pipe.inlet = MarkElementWidget()
    pipe.outlet = MarkElementWidget()
    sends: list[dict] = []
    pipe.send = lambda content, *_a, **_k: sends.append(content)

    runner = asyncio.create_task(pipe.run())
    await _ticks()
    assert sends == [{"action": "run", "gen": 1}]

    def answer() -> None:
        assert threading.current_thread().name == "subshell"
        pipe.outlet.set_state({"value": {"id": "laid-out"}, "gen": 1})

    started = monotonic()
    subshell.call_soon_threadsafe(answer)
    done, _pending = await asyncio.wait({runner}, timeout=PROMPT)
    elapsed = monotonic() - started

    assert runner in done, f"runner still parked after {elapsed:.3f}s"
    assert elapsed < PROMPT
    assert runner.exception() is None
    assert pipe.outlet.value.id == "laid-out"
    assert sends == [{"action": "run", "gen": 1}], "no re-send of an answered request"


@pytest.mark.asyncio
async def test_schedule_run_from_another_loop_hands_over(subshell):
    """A runner scheduled from a cell (main loop) is alive when a widget
    callback on the subshell loop requests a run: the callback gets a runner
    on *its* loop, the old runner is cancelled, the request count survives,
    and the flow the old run took is re-recorded for the new one.
    """
    main = asyncio.get_running_loop()
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.record(F.New)

    old = pipeline.schedule_run()
    await _ticks()
    assert old.get_loop() is main
    assert parked.runs == 1
    assert pipeline.inlet.flow == (), "the old run took the flow"
    assert pipeline._requested == 1

    async def from_subshell() -> asyncio.Task:
        assert asyncio.get_running_loop() is subshell
        new = pipeline.schedule_run()
        assert new is not old, "a foreign-loop runner is not reused"
        assert new.get_loop() is subshell, "awaitable by the caller"
        assert pipeline._task is new
        assert pipeline._requested == 2, "the request is kept"
        assert pipeline.inlet.flow == (F.New,), "the taken flow is handed back"
        # the cancel crosses to the main loop; let it land before releasing
        # the gate, so the old run cannot complete instead of being cancelled
        for _ in range(200):
            if old.done():
                break
            await asyncio.sleep(0.01)
        assert old.done()
        assert old.cancelled()
        parked.release()
        await asyncio.wait_for(new, timeout=2.0)  # same loop: plain await works
        return new

    new = await _on(subshell, from_subshell())

    with pytest.raises(asyncio.CancelledError):
        await old
    assert not new.cancelled()
    assert new.exception() is None
    assert parked.runs == 2, "the new runner re-ran with the re-recorded flow"
    assert parked.loops == [main, subshell]
    assert pipeline.inlet.flow == (), "consumed by the run that completed"
    assert pipeline.status.exception is None


@pytest.mark.asyncio
async def test_cancel_from_another_thread_lands_on_the_runners_loop(subshell):
    """``cancel`` from the subshell thread reaches a main-loop runner without
    waiting for that loop's next timer.
    """
    parked = _Parked(observes=(F.New,), reports=(F.Layout,))
    pipeline = Pipeline(pipes=[parked])
    pipeline.inlet.record(F.New)
    task = pipeline.schedule_run()
    await _ticks()

    # a bare callback on the subshell thread: nothing else (such as the
    # completion of a coroutine awaited from here) wakes the main loop
    started = monotonic()
    subshell.call_soon_threadsafe(pipeline.cancel)
    done, _pending = await asyncio.wait({task}, timeout=PROMPT)
    elapsed = monotonic() - started

    assert task in done
    assert task.cancelled()
    assert elapsed < PROMPT, f"cancel only landed at a timer, after {elapsed:.3f}s"
    assert pipeline.inlet.flow == (F.New,), "the taken flow is handed back"
    assert pipeline._task is None
