# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import Callable

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import Pipe


class Tool(W.Widget):
    tee: Pipe = T.Instance(Pipe, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    on_done = T.Any(allow_none=True)  # callback when done
    disable = T.Bool(default_value=False).tag(sync=True, **W.widget_serialization)
    reports = TypedTuple(T.Unicode(), kw={})
    _task: asyncio.Future = None
    ui = T.Instance(W.DOMWidget, allow_none=True)
    priority = T.Int(default_value=10)
    _on_run_handlers = W.CallbackDispatcher()

    def handler(self, *args):
        """Handler callback for running the tool"""
        # canel old work if needed
        if self._task:
            self._task.cancel()

        # schedule work
        self._task = asyncio.create_task(self.run())

        # callback
        self._task.add_done_callback(self._finished)

        if self.tee:
            self.tee.inlet.flow = self.reports

    async def run(self):
        raise NotImplementedError()

    # TODO reconcile `on_run` and `on_done`
    def on_run(self, callback, remove=False):
        """Register a callback to execute when the button is clicked.
        The callback will be called with one argument, the clicked button
        widget instance.
        Parameters
        ----------
        remove: bool (optional)
            Set to true to remove the callback from the list of callbacks.
        """
        self._on_run_handlers.register_callback(callback, remove=remove)

    def _finished(self, future: asyncio.Future):
        try:
            future.result()
            self._on_run_handlers(self)
            if callable(self.on_done):
                self.on_done()
        except asyncio.CancelledError:
            pass  # cancellation should not log an error
        except Exception:
            self.log.exception(f"Error running tool: {type(self)}")


class ToolButton(Tool):
    """Generic Tool that provides a simple button UI

    :param handler: Called when button is pressed.
    """

    handler: Callable = T.Any(allow_none=True)
    description: str = T.Unicode(default_value="")

    @T.default("ui")
    def _default_ui(self):
        btn = W.Button(description=self.description)
        T.link((self, "description"), (btn, "description"))

        def click(*args):
            if callable(self.handler):
                self.handler()

        btn.on_click(click)
        return btn
