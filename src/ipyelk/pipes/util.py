# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import os
from time import monotonic
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ipywidgets as W

    from ..diagram.viewer import Viewer
    from .base import SyncedPipe


def wait_for_change(widget, value, timeout: float | None = None):
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
    max_delay: float = 2.0,
    timeout: float | None = None,
):
    """Send ``{"action": "run"}`` to a synced pipe's frontend and wait for the
    pipe's outlet to change.

    ``Widget.send`` only reaches a frontend that is already attached: a pipe
    that runs before its diagram is displayed (the common notebook flow --
    build in one cell, render later) would otherwise wait on a message nobody
    received. The request is therefore re-sent with backoff until one of:

    * the outlet changes -- the browser answered; re-sending is idempotent,
      so retrying converges as soon as a frontend attaches. ``max_delay`` caps
      the backoff low: the first request is usually the one that is lost (the
      diagram is not on the page yet), and a frontend that attaches a second
      later should not wait out a ten second gap before anything renders;
    * the browser reports a failure -- an ``action: error`` message rejects
      the pending future (see ``SyncedPipe._handle_browser_msg``): an errored
      run must stop the retries, not feed them;
    * the ``timeout`` deadline passes -- :class:`asyncio.TimeoutError`, so a
      permanently silent browser cannot hang the kernel forever.

    When ``IPYELK_NO_BROWSER`` is set there is no frontend to wait for at all
    (``nbconvert --execute``, doctests): waiting is pointless, and keeping a
    task alive that re-sends comm messages across cell boundaries has wedged
    kernels on slow CI runners. Give up immediately so each pipe takes its
    existing "browser did not answer" path.
    """
    if os.environ.get("IPYELK_NO_BROWSER"):
        raise asyncio.TimeoutError

    future_value = wait_for_change(pipe.outlet, trait)
    pipe._roundtrip_future = future_value
    # a fresh roundtrip resets the stale re-sync throttle (see SyncedPipe)
    pipe._stale_resync_interval = 0.0
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


def resync_stale(
    widget: SyncedPipe | Viewer,
    *others: W.Widget | None,
    missing: object = None,
    min_interval: float = 2.0,
    max_interval: float = 30.0,
) -> bool:
    """Re-send the state of ``widget`` and ``others`` after the browser reports
    ``action: stale``; ``False`` when throttled.

    Widget state sync has no retransmit, and jupyter-server's iopub rate
    limiter silently drops ``comm_msg`` under bursty load (a run-all creating
    many diagrams), leaving a frontend model that can never serve a request.
    The re-sync goes over the same congested channel, so it is throttled: the
    gap doubles between ``min_interval`` and ``max_interval`` per re-sync; a
    caller starting fresh work resets ``widget._stale_resync_interval``.
    """
    now = monotonic()
    interval = widget._stale_resync_interval
    if now - widget._stale_resync_at < interval:
        return False
    widget._stale_resync_at = now
    widget._stale_resync_interval = min(max(min_interval, interval * 2), max_interval)
    widget.log.debug(
        "Browser reports stale state for %s (missing: %s); re-syncing",
        type(widget).__name__,
        missing,
    )
    for w in (widget, *others):
        if w is not None:
            w.send_state()
    return True
