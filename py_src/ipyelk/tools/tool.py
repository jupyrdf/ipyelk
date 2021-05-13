# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..pipes import MarkElementWidget, Pipe


class Tool(W.Widget):
    tee: Pipe = T.Instance(Pipe, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    on_done = T.Any(allow_none=True)  # callback when done
    disable = T.Bool(default_value=False).tag(sync=True, **W.widget_serialization)
    reports = TypedTuple(T.Unicode(), kw={})

    def handler(self, *args):
        """Handler callback for running the tool"""
        # schedule work
        task = asyncio.create_task(self.run())

        # callback
        task.add_done_callback(self._finished)

        if self.tee:
            self.tee.inlet.flow = self.reports

    async def run(self):
        raise NotImplementedError()

    def _finished(self, future: asyncio.Future):
        try:
            future.result()
            if callable(self.on_done):
                self.on_done()
        except asyncio.CancelledError:
            pass  # cancellation should not log an error
        except Exception:
            self.log.exception(f"Error running tool: {type(self)}")

