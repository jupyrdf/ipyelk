# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
from time import monotonic
from typing import Optional


def wait_for_change(widget, value, timeout: Optional[float] = None):
    """Return a future that resolves when ``widget``'s ``value`` trait changes.

    Initial pattern from the ipywidgets async docs. If ``timeout`` is given and
    no change occurs within that many seconds, the future is rejected with
    :class:`asyncio.TimeoutError` so callers never hang indefinitely.
    """
    future: asyncio.Future = asyncio.Future()

    def getvalue(change):
        """Make the new value available"""
        if not future.done():
            future.set_result(change.new)

    def unobserve(f):
        """Unobserves the `getvalue` callback"""
        widget.unobserve(getvalue, value)

    future.add_done_callback(unobserve)
    widget.observe(getvalue, value)

    if timeout is not None:
        loop = asyncio.get_event_loop()

        def on_timeout():
            if not future.done():
                future.set_exception(asyncio.TimeoutError())

        timer = loop.call_later(timeout, on_timeout)
        future.add_done_callback(lambda _: timer.cancel())

    return future


async def browser_roundtrip(
    pipe,
    trait: str = "value",
    initial_delay: float = 0.5,
    max_delay: float = 10.0,
    timeout: Optional[float] = None,
):
    """Send ``{"action": "run"}`` to a synced pipe's frontend and wait for the
    pipe's outlet to change.

    ``Widget.send`` only reaches a frontend that is already attached: a pipe
    that runs before its diagram is displayed (the common notebook flow --
    build in one cell, render later) would otherwise wait on a message nobody
    received. The request is therefore re-sent with backoff until one of:

    * the outlet changes -- the browser answered; re-sending is idempotent,
      so retrying converges as soon as a frontend attaches;
    * the browser reports a failure -- an ``action: error`` message rejects
      the pending future (see ``SyncedPipe._handle_browser_msg``): an errored
      run must stop the retries, not feed them;
    * the ``timeout`` deadline passes -- :class:`asyncio.TimeoutError`, so a
      permanently silent browser cannot hang the kernel forever.
    """
    future_value = wait_for_change(pipe.outlet, trait)
    pipe._roundtrip_future = future_value
    deadline = None if timeout is None else monotonic() + timeout
    delay = initial_delay
    try:
        while True:
            pipe.send({"action": "run"})
            wait = delay
            if deadline is not None:
                wait = min(delay, max(deadline - monotonic(), 0.01))
            try:
                await asyncio.wait_for(asyncio.shield(future_value), wait)
            except asyncio.TimeoutError:
                if deadline is not None and monotonic() >= deadline:
                    future_value.cancel()
                    raise
                delay = min(delay * 2, max_delay)
            except asyncio.CancelledError:
                future_value.cancel()
                raise
            else:
                return
    finally:
        pipe._roundtrip_future = None
