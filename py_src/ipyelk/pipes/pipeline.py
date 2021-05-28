# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Callable, Optional, Tuple

import ipywidgets as W
import traitlets as T

from ..exceptions import BrokenPipe
from .base import Pipe, PipeDisposition, SyncedOutletPipe


class Pipeline(SyncedOutletPipe):
    pipes: Tuple[Pipe] = T.List(T.Instance(Pipe), kw={}).tag(
        sync=True, **W.widget_serialization
    )
    on_progress: Optional[Callable] = T.Any(allow_none=True)
    exception = T.Instance(Exception, allow_none=True)

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
        self.exception = None
        self.check_dirty()

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            # TODO use i and num_steps for reporting processing stage
            p_name = f"pipe {i}: {type(pipe)}"
            if pipe.dirty:
                self.status_update(pipe, PipeDisposition.running)
                try:
                    await pipe.run()
                except Exception as err:
                    self.log.exception(f"Error running {p_name}")
                    self.status_update(pipe, PipeDisposition.error, exception=err)
                    raise err
                pipe.dirty = False
            else:
                pipe.outlet.value = pipe.inlet.value
            self.status_update(pipe, PipeDisposition.done)
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
            self.disposition = PipeDisposition.waiting
        else:
            self.dirty = False
            self.disposition = PipeDisposition.done

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

    def status_update(
        self, pipe: Pipe, disposition: PipeDisposition, *, exception: Exception = None
    ):
        pipe.disposition = disposition
        if exception:
            self.exception = exception

        if callable(self.on_progress):
            self.on_progress(self, pipe)
