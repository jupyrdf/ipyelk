# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import Tuple

import ipywidgets as W
import traitlets as T

from ..elements import EMPTY_SENTINEL, Node, elk_serialization
from ..exceptions import BrokenPipe


class MarkElementWidget(W.DOMWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)

    def to_id(self):
        pass

    def from_id(self):
        pass


class SyncedMarkElementWidget(MarkElementWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)


class Pipe(W.Widget):
    enabled: bool = T.Bool(default_value=True)
    inlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    outlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def schedule_run(self, change: T.Bunch = None):
        # schedule task on loop
        asyncio.create_task(self.run())

    async def run(self):
        # do work
        self.outlet = self.inlet
        return self.outlet


class SyncedInletPipe(Pipe):
    inlet = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedOutletPipe(Pipe):
    outlet = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedPipe(SyncedOutletPipe, SyncedInletPipe):
    """Both inlet and value are synced with the browser"""


class Pipeline(SyncedOutletPipe):
    pipes: Tuple[Pipe] = T.List(T.Instance(Pipe), kw={}).tag(
        sync=True, **W.widget_serialization
    )

    @T.observe("pipes", "inlet")
    def _update_pipes(self, change=None):
        prev = self.inlet
        for pipe in self.pipes:
            pipe.inlet = prev
            prev = pipe.outlet
        self.outlet = prev

        self.schedule_run()

    async def run(self, start_pipe=None, value=EMPTY_SENTINEL):
        pipes = self.pipes
        if start_pipe and start_pipe in pipes:
            start = pipes.index(start_pipe)
            pipes = pipes[start:]

        if value is not EMPTY_SENTINEL:
            pipes[0].inlet.value = value

        num_steps = len(pipes)

        # Look at enabled pipes
        for i, pipe in enumerate(pipes):
            # TODO use i for reporting processing stage
            await pipe.run()

    def check(self) -> bool:
        """Checks inlets and outlets of the pipeline and raises error is not connected

        :raises BrokenPipe: Disconnected pipes
        :return: True if no errors in pipeline
        """
        broken = []
        prev = self.inlet
        for i, pipe in enumerate(self.pipes):
            if prev is not pipe.inlet:
                broken.append((i - 1, i))
            prev = pipe.outlet

        if prev is not self.outlet:
            broken.append((i, i + 1))

        if broken:
            raise BrokenPipe(broken)
        return True
