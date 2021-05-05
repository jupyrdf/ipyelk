# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
import re
from typing import Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    BaseElement,
    ElementIndex,
    HierarchicalElement,
    Node,
    elk_serialization,
)
from ..exceptions import BrokenPipe


class MarkElementWidget(W.DOMWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)
    _index = T.Instance(ElementIndex, allow_none=True)
    flow = TypedTuple(T.Unicode(), kw={})

    @T.observe("value")
    def reset_index(self, change=None):
        self._index = None

    def get_index(self) -> ElementIndex:
        if self._index is None:
            self._index = ElementIndex.from_els(self.value)
        return self._index

    def to_id(self, element: BaseElement):
        return element.get_id()

    def from_id(self, key) -> HierarchicalElement:
        return self.get_index().get(key)


class SyncedMarkElementWidget(MarkElementWidget):
    value = T.Instance(Node, allow_none=True).tag(sync=True, **elk_serialization)


class Pipe(W.Widget):
    enabled: bool = T.Bool(default_value=True)
    inlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    outlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    dirty: bool = T.Bool(default_value=True)
    observes: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    reports: Tuple[str] = TypedTuple(T.Unicode(), kw={})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def schedule_run(self, change: T.Bunch = None) -> asyncio.Task:
        # schedule task on loop
        return asyncio.create_task(self.run())

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

    @T.observe("pipes", "inlet")
    def _update_pipes(self, change=None):
        prev = self.inlet
        for pipe in self.pipes:
            pipe.inlet = prev
            prev = pipe.outlet
        self.outlet = prev

        self.schedule_run()

    async def run(self):
        self.check_dirty()

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            # TODO use i and num_steps for reporting processing stage
            if pipe.dirty:
                await pipe.run()
                pipe.dirty = False
            else:
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
            prev = pipe.outlet

        if prev is not self.outlet:
            broken.append((i, i + 1))

        if broken:
            raise BrokenPipe(broken)
        return True
