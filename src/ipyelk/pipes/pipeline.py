# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
from datetime import datetime

import ipywidgets as W
import traitlets as T

from ..exceptions import BrokenPipe
from .base import Pipe, PipeStatus, PipeStatusView, SyncedOutletPipe


class PipelineStatusView(PipeStatusView):
    toggle_btn = T.Instance(W.Button)
    include_exception = T.Bool(default_value=True)
    collapsed = T.Bool(default_value=True)
    statuses = T.List(T.Instance(W.Widget), default_value=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @T.default("toggle_btn")
    def _default_toggle(self):
        btn = W.Button(icon="chevron-down").add_class("elk-pipe-toggle-btn")
        toggle_cls = "elk-pipe-closed"

        @btn.on_click
        def toggle(b):
            self.collapsed = not self.collapsed
            if self.collapsed:
                btn.add_class(toggle_cls)
            else:
                btn.remove_class(toggle_cls)

        return btn

    @T.observe("collapsed", "statuses")
    def _update_children(self, change=None):
        children = [
            W.HBox([
                self.toggle_btn,
                self.html,
            ]),
        ]
        if not self.collapsed:
            children.extend(self.statuses)
        self.children = children

    def update_children(self, pipe: Pipeline):
        statuses = [p.status_widget for p in pipe.pipes]
        self.statuses = [
            W.HBox([
                W.HTML(value="<pre>  </pre>").add_class("elk-pipe-space"),
                status,
                W.HTML(value=f'<pre class="elk-pipe-accessor">.pipes[{i}]</pre>'),
            ])
            for i, status in enumerate(statuses)
        ]


class Pipeline(SyncedOutletPipe):
    pipes = T.List(T.Instance(Pipe), kw={}).tag(sync=True, **W.widget_serialization)

    #: what the in-flight run took from ``inlet.flow``; owed back if it does
    #: not complete (see ``run`` and ``schedule_run``)
    _taken: tuple[str, ...] = ()

    @T.default("status_widget")
    def _default_status_widget(self):
        widget = PipelineStatusView()

        def update(change: T.Bunch | None = None):
            widget.update(self)

        update()
        self.observe(update, "status")
        return widget

    @T.observe("pipes", "inlet")
    def _update_pipes(self, change=None):
        prev = self.inlet
        for pipe in self.pipes:
            pipe.inlet = prev
            pipe.outlet.index = pipe.inlet.index
            prev = pipe.outlet
        self.outlet = prev

        # self.schedule_run()

    def schedule_run(self, change: T.Bunch | None = None) -> asyncio.Task | None:
        # ``Pipe.schedule_run`` cancels the in-flight run, but cancellation
        # unwinds on a later loop turn (``wait_for`` on Python < 3.12 awaits
        # its inner future first) -- possibly after the successor has already
        # taken the pending flow and found nothing.  Hand the in-flight run's
        # tags back now, before the successor exists.
        self._release_taken()
        return super().schedule_run(change)

    def _release_taken(self) -> None:
        taken, self._taken = self._taken, ()
        if taken:
            self.inlet.record(*taken)

    async def run(self):
        start = datetime.now()
        # take at start: a tag recorded while this run is in flight stays
        # pending for the next run instead of being erased when this one
        # completes; only a *successful* run consumes what it took
        self._taken = taken = self.inlet.take()
        try:
            await self._run_pipes(taken)
        except BaseException:
            # a failed or cancelled run retries: re-record what it took (unless
            # ``schedule_run`` already handed it to a successor)
            if self._taken is taken:
                self._release_taken()
            raise
        self._taken = ()
        self.status_update(PipeStatus.finished(start_time=start))

    async def _run_pipes(self, flow: tuple[str, ...]) -> None:
        self.check_dirty(flow)

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            # TODO use i and num_steps for reporting processing stage
            pipe_start_time = datetime.now()
            p_name = f"pipe {i}: {type(pipe)}"
            try:
                if pipe.status.dirty():
                    self.status_update(PipeStatus.running(), pipe=pipe)
                    await pipe.run()
                else:
                    pipe.outlet.value = pipe.inlet.value
            except Exception as err:
                self.log.exception(f"Error running {p_name}")
                self.status_update(
                    PipeStatus.error(
                        exception=err,
                        start_time=pipe_start_time,
                    ),
                    pipe=pipe,
                )
                raise err

            pipe.status_update(PipeStatus.finished(start_time=pipe_start_time))

    def check_dirty(self, flow: tuple[str, ...] | None = None) -> bool:
        # check pipes and propagate flow to downstream pipes; ``flow`` (the
        # run's taken flow) feeds the first pipe, later pipes read what their
        # predecessor propagated to its outlet
        observes = set()
        reports = set()
        for i, pipe in enumerate(self.pipes):
            if pipe.check_dirty(flow if i == 0 else None):
                observes |= set(pipe.observes)
                reports |= set(pipe.reports)
        # pipeline is dirty if flows are added to reports from subpipes
        if len(reports):
            self.status = PipeStatus.waiting()
        else:
            self.status = PipeStatus.finished()

        self.observes = tuple(observes)
        self.reports = tuple(reports)
        return self.status.dirty()

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
            last_pipe_index = len(self.pipes) - 1
            broken.append((last_pipe_index, last_pipe_index + 1))

        if broken:
            raise BrokenPipe(broken)
        return True

    def get_progress_value(self) -> float:
        if not self.pipes:
            return 1.0
        return sum(pipe.get_progress_value() for pipe in self.pipes) / len(self.pipes)
