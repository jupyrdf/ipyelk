# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from datetime import datetime

import ipywidgets as W
import traitlets as T

from ..exceptions import BrokenPipe
from .base import Pipe, PipeStatus, PipeStatusView, Superseded, SyncedOutletPipe


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

    #: what the in-flight run took from ``inlet.flow``; re-recorded if it fails
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

    def cancel(self) -> bool:
        """Cancel, and re-record the in-flight run's tags now: the cancellation
        unwinds a loop turn later, after a new runner may already have taken.
        """
        cancelled = super().cancel()
        if cancelled:
            self._release_taken()
        return cancelled

    def _release_taken(self) -> None:
        taken, self._taken = self._taken, ()
        if taken:
            self.inlet.record(*taken)

    async def run(self, flow: tuple[str, ...] | None = None):
        """Run the dirty pipes for the pending flow.

        The flow is taken from the inlet at the start (``MarkElementWidget.take``)
        and re-recorded unless the run succeeds. A source should therefore feed
        one pipeline: a second would find the flow already taken.

        ``flow`` is passed by a parent pipeline to a nested one, since the
        parent already took it.
        """
        start = datetime.now()
        if flow is None:
            self._taken = taken = self.inlet.take()
        else:
            taken = flow
        try:
            await self._run_pipes(taken)
        except BaseException:
            if flow is None and self._taken is taken:
                self._release_taken()
            raise

        if self._taken is taken:
            self._taken = ()
        self.status_update(PipeStatus.finished(start_time=start))

    async def _run_pipes(self, flow: tuple[str, ...]) -> None:
        self.check_dirty(flow)

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            if i and self.superseded():
                raise Superseded(f"superseded before stage {i}")
            # TODO use i and num_steps for reporting processing stage
            pipe_start_time = datetime.now()
            p_name = f"pipe {i}: {type(pipe)}"
            try:
                await self._run_pipe(i, pipe, flow)
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

    async def _run_pipe(self, i: int, pipe: Pipe, flow: tuple[str, ...]) -> None:
        if not pipe.status.dirty():
            pipe.outlet.value = pipe.inlet.value
            return
        self.status_update(PipeStatus.running(), pipe=pipe)
        if isinstance(pipe, Pipeline):
            await pipe.run(flow=flow if i == 0 else pipe.inlet.flow)
        else:
            await pipe.run()

    def check_dirty(self, flow: tuple[str, ...] | None = None) -> bool:
        # check pipes and propagate flow to downstream pipes
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
