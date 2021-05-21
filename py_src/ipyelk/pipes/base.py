# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
import re
from enum import Enum
from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .marks import MarkElementWidget


class PipeDisposition(Enum):
    waiting = "waiting"
    running = "running"
    done = "finished"
    error = "error"


class Pipe(W.Widget):
    disposition = T.Instance(PipeDisposition)
    enabled: bool = T.Bool(default_value=True)
    inlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    outlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    dirty: bool = T.Bool(default_value=True)
    observes: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    reports: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    _task: asyncio.Future = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def schedule_run(self, change: T.Bunch = None) -> asyncio.Task:
        # schedule task on loop
        if self._task:
            self._task.cancel()
        self._task = asyncio.create_task(self.run())

        self._task.add_done_callback(self._post_run)
        return self._task

    def _post_run(self, future: asyncio.Future):
        try:
            future.exception()
        except asyncio.CancelledError:
            pass
        except Exception as E:
            raise E

    async def run(self):
        # do work
        self.outlet.value = self.inlet.value

    def check_dirty(self) -> bool:
        flow = self.inlet.flow

        if any(any(re.match(f"^{obs}$", f) for f in flow) for obs in self.observes):
            # mark this pipe as dirty so will run
            self.dirty = True
            self.disposition = PipeDisposition.waiting
            # add this pipes reporting to the outlet flow
            flow = tuple(set([*flow, *self.reports]))
        else:
            self.dirty = False
            self.disposition = PipeDisposition.done
        self.outlet.flow = flow
        return self.dirty


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
