# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio

import ipywidgets as W
import traitlets as T

from ..pipes import MarkElementWidget, Pipe


class Tool(W.Widget):
    tee: Pipe = T.Instance(Pipe, allow_none=True).tag(
        sync=True, **W.widget_serialization
    )
    on_done = T.Any(allow_none=True)  # callback when done
    disable = T.Bool(default_value=False).tag(sync=True, **W.widget_serialization)

    def handler(self, *args):
        """Handler callback for running the tool"""
        # schedule work
        task = asyncio.create_task(self.run())

        # callback
        if callable(self.on_done):
            task.add_done_callback(self.on_done)

    async def run(self):
        # mark clamped pipe as dirty
        if self.tee:
            self.tee.dirty = True


class Loader(Tool):
    def load(self) -> MarkElementWidget:
        pass
