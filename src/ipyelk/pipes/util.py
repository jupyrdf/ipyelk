# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
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
