# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import asyncio
from typing import Tuple

import ipywidgets as W
import traitlets as T

from ..elements import Node, elk_serialization
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
    source: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    value: MarkElementWidget = T.Instance(MarkElementWidget, kw={})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def schedule_run(self, change: T.Bunch = None):
        # schedule task on loop
        asyncio.create_task(self.run())

    async def run(self):
        # do work
        self.value = self.source
        return self.value


class SyncedSourcePipe(Pipe):
    source = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedValuePipe(Pipe):
    value = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedPipe(SyncedValuePipe, SyncedSourcePipe):
    """Both source and value are synced with the browser"""


class Pipeline(SyncedValuePipe):
    pipes: Tuple[Pipe] = T.List(T.Instance(Pipe), kw={}).tag(
        sync=True, **W.widget_serialization
    )

    @T.observe("pipes", "source")
    def _update_pipes(self, change=None):
        prev = self.source
        for pipe in self.pipes:
            pipe.source = prev
            prev = pipe.value
        self.value = prev

        self.schedule_run()

    async def run(self):
        for i, pipe in enumerate(self.pipes):
            # TODO use i for reporting processing stage
            await pipe.run()

    def check(self) -> bool:
        """Checks sources and values of the pipeline and raises error is not connected

        :raises BrokenPipe: Disconnected pipes
        :return: True if no errors in pipeline
        """
        broken = []
        prev = self.source
        for i, pipe in enumerate(self.pipes):
            if prev is not pipe.source:
                broken.append((i - 1, i))
            prev = pipe.value

        if prev is not self.value:
            broken.append((i, i + 1))

        if broken:
            raise BrokenPipe(broken)
        return True
