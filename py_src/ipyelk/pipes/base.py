# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
import re
from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..exceptions import BrokenPipe
from .marks import MarkElementWidget


class Pipe(W.Widget):
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
            # add this pipes reporting to the outlet flow
            flow = tuple(set([*flow, *self.reports]))
        else:
            self.dirty = False
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


class Pipeline(SyncedOutletPipe):
    pipes: Tuple[Pipe] = T.List(T.Instance(Pipe), kw={}).tag(
        sync=True, **W.widget_serialization
    )
    # TODO need to keep track of the run task and cancel / debounce as needed

    @T.observe("pipes", "inlet")
    def _update_pipes(self, change=None):
        prev = self.inlet
        for pipe in self.pipes:
            pipe.inlet = prev
            pipe.outlet.index = pipe.inlet.index
            prev = pipe.outlet
        self.outlet = prev

        self.schedule_run()

    async def run(self):
        self.check_dirty()

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            # TODO use i and num_steps for reporting processing stage
            p_name = f"pipe {i}: {type(pipe)}"
            if pipe.dirty:
                self.log.warning(f"Running {p_name}")
                try:
                    await pipe.run()
                except Exception as err:
                    self.log.exception(f"Error running {p_name}")
                    raise err
                pipe.dirty = False
                self.log.warning(f"Done running {p_name}")
            else:
                self.log.warning(f"Passthrough {p_name}")
                pipe.outlet.value = pipe.inlet.value
        self.dirty = False

    def check_dirty(self) -> bool:
        # check pipes and propagate flow to downstream pipes
        observes = set()
        reports = set()
        for pipe in self.pipes:
            if pipe.check_dirty():
                observes |= set(pipe.observes)
                reports |= set(pipe.reports)
        # pipeline is dirty if flows are added to reports from subpipes
        if len(reports):
            self.dirty = True
        else:
            self.dirty = False

        self.observe = tuple(observes)
        self.reports = tuple(reports)
        return self.dirty

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
            assert pipe.outlet.index is pipe.inlet.index
            prev = pipe.outlet

        if prev is not self.outlet:
            broken.append((i, i + 1))

        if broken:
            raise BrokenPipe(broken)
        return True
