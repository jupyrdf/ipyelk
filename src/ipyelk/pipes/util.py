# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import contextlib
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


def on_own_loop(future: asyncio.Future) -> bool:
    """Whether the calling thread is running ``future``'s event loop."""
    try:
        return asyncio.get_running_loop() is future.get_loop()
    except RuntimeError:
        return False


def settle(future: asyncio.Future, method: str, *args) -> None:
    """Call ``future.<method>(*args)`` (``set_result``/``set_exception``) on
    the loop the future belongs to, from whatever thread this runs on.

    With ipykernel >= 7 and kernel subshells (JupyterLab 4.5+, ipywidgets
    8.1.8+), widget messages arrive on a subshell thread with its own loop,
    while a runner started from a cell lives on the main loop. Settling a
    future from another thread neither is safe nor wakes its loop, so it goes
    through ``call_soon_threadsafe``. A future already done is left alone.
    """

    def apply():
        if not future.done():
            getattr(future, method)(*args)

    if on_own_loop(future):
        apply()
        return
    with contextlib.suppress(RuntimeError):
        future.get_loop().call_soon_threadsafe(apply)


def wait_for_answer(pipe, gen: int, trait: str = "value") -> asyncio.Future:
    """Return a future that resolves (with ``outlet.value``) when the browser
    answers roundtrip ``gen``.

    The frontend writes ``gen`` and ``value`` in one ``save_changes``
    (``answer`` in ``js/layout_widget_util.ts``). Both traits are observed
    because an answer identical to the previous one may arrive as a change of
    ``gen`` alone.

    An answer for another generation is ignored. ``gen == 0`` (an older
    extension build) is accepted, with one warning per pipe, but only when the
    browser wrote it (``value`` in ``_property_lock``), not the kernel.
    """
    outlet = pipe.outlet
    future: asyncio.Future = asyncio.get_running_loop().create_future()

    def on_change(change):
        if future.done():
            return
        answered = outlet.gen
        from_browser = "value" in outlet._property_lock
        if answered == gen:
            settle(future, "set_result", outlet.value)
        elif answered == 0 and from_browser:
            if not getattr(pipe, "_warned_unversioned", False):
                pipe._warned_unversioned = True
                pipe.log.warning(
                    "The frontend answered a %s run without a generation "
                    "(older extension build?); accepting it, but a stale answer "
                    "cannot be told from a fresh one",
                    type(pipe).__name__,
                )
            settle(future, "set_result", outlet.value)
        elif answered == 0:
            pipe.log.debug(
                "%s ignoring a kernel-side %s write while waiting for generation %s",
                type(pipe).__name__,
                change.name,
                gen,
            )
        else:
            pipe.log.debug(
                "%s ignoring browser answer for generation %s while waiting for %s",
                type(pipe).__name__,
                answered,
                gen,
            )

    names = [trait, "gen"]
    future.add_done_callback(lambda _: outlet.unobserve(on_change, names))
    outlet.observe(on_change, names)
    return future


async def browser_roundtrip(
    pipe,
    trait: str = "value",
    initial_delay: float = 0.5,
    max_delay: float = 2.0,
    timeout: float | None = None,
):
    """Send ``{"action": "run", "gen": g}`` to a synced pipe's frontend and
    wait for the pipe's outlet to be written for generation ``g``.

    ``g`` counts this pipe's roundtrips; the frontend stamps its answer with
    it (``outlet.gen``) so an answer to an earlier, abandoned request is
    never taken for this one (``wait_for_answer``), and so a re-sent request
    is recognised as the same work and not laid out twice.

    ``Widget.send`` only reaches a frontend that is already attached: a pipe
    that runs before its diagram is displayed (the common notebook flow --
    build in one cell, render later) would otherwise wait on a message nobody
    received. The request is therefore re-sent with backoff until one of:

    * the browser writes the outlet for generation ``g`` (``wait_for_answer``
      watches ``value`` and ``gen``); re-sending is idempotent, so retrying
      converges as soon as a frontend attaches. ``max_delay`` caps
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

    pipe._roundtrip_gen = gen = getattr(pipe, "_roundtrip_gen", 0) + 1
    future_value = wait_for_answer(pipe, gen, trait)
    pipe._roundtrip_future = future_value
    # a fresh roundtrip resets the stale re-sync throttle (see SyncedPipe)
    pipe._stale_resync_interval = 0.0
    deadline = None if timeout is None else monotonic() + timeout
    delay = initial_delay
    try:
        while True:
            pipe.send({"action": "run", "gen": gen})
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
        # a successor may already be waiting on its own future
        if pipe._roundtrip_future is future_value:
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
