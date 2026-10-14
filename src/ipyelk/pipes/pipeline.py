# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from datetime import datetime

import ipywidgets as W
import traitlets as T

from ..exceptions import BrokenPipe
from ..util import close_widget
from .base import Pipe, PipeStatus, PipeStatusView, Superseded, SyncedOutletPipe
from .util import iter_pipes


class PipelineStatusView(PipeStatusView):
    toggle_btn = T.Instance(W.Button)
    header = T.Instance(W.HBox, kw={})
    include_exception = T.Bool(default_value=True)
    collapsed = T.Bool(default_value=True)

    def __init__(self, *args, **kwargs):
        #: one row per sub-pipe, shown below the header when expanded
        self._rows: list[W.HBox] = []
        #: the sub-pipes and their views that ``_rows`` was built for
        self._row_key: tuple | None = None
        #: widgets ``update_children`` created; closed when the rows are rebuilt
        self._owned: list[W.Widget] = []
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

    @T.observe("collapsed")
    def _update_children(self, change=None):
        self.header.children = [self.toggle_btn, self.html]
        children = [self.header]
        if not self.collapsed:
            children.extend(self._rows)
        self.children = children

    def update_children(self, pipe: Pipeline):
        """Show one row per sub-pipe, rebuilding the rows only when the sub-pipes
        or their views change.
        """
        key = tuple((p, p.status_widget) for p in pipe.pipes)
        if key != self._row_key:
            self._row_key = key
            stale, self._owned = self._owned, []
            self._rows = [self._row(i, view) for i, (_, view) in enumerate(key)]
            for widget in stale:
                close_widget(widget)
        self._update_children()

    def close(self):
        for widget in self._owned:
            close_widget(widget)
        self._owned = []
        for name in ("toggle_btn", "header"):
            widget = self._trait_values.get(name)
            if widget is not None:
                close_widget(widget)
        super().close()

    def _row(self, i: int, view: W.DOMWidget) -> W.HBox:
        space = W.HTML(value="<pre>  </pre>").add_class("elk-pipe-space")
        accessor = W.HTML(value=f'<pre class="elk-pipe-accessor">.pipes[{i}]</pre>')
        row = W.HBox([space, view, accessor])
        self._owned += [row, space, accessor]
        return row


class Pipeline(SyncedOutletPipe):
    pipes = T.List(T.Instance(Pipe), kw={}).tag(sync=True, **W.widget_serialization)

    #: what the in-flight run took from ``inlet.flow``; re-recorded if it fails
    _taken: tuple[str, ...] = ()
    #: the stages ``pipes`` last accepted; the trait may already hold a proposal
    _stages: tuple[Pipe, ...] = ()

    @T.default("status_widget")
    def _default_status_widget(self):
        widget = PipelineStatusView()

        def update(change: T.Bunch | None = None):
            widget.update(self)

        update()
        self.observe(update, "status")
        return self._own(widget)

    def close(self):
        """Close this pipeline, its sub-pipes and the widgets it created."""
        for pipe in self.pipes:
            pipe.close()
        super().close()

    @T.validate("pipes")
    def _validate_pipes(self, proposal: T.Bunch) -> list[Pipe]:
        """Refuse a closed stage, a stage listed twice, or a new stage that is
        part of an open diagram's pipe.
        """
        pipes = proposal["value"]
        kept = {id(pipe) for pipe in self._stages}
        seen: set[int] = set()
        for stage in pipes:
            if id(stage) in seen:
                msg = f"{type(stage).__name__} is listed twice; use a new pipe"
            else:
                msg = None if id(stage) in kept else self._refusal(stage)
            seen.add(id(stage))
            if msg:
                if self.comm is None:
                    # or collecting a half-built pipeline would close them
                    self._trait_values.pop("pipes", None)
                raise T.TraitError(msg)
        self._stages = tuple(pipes)
        return pipes

    def _refusal(self, stage: Pipe) -> str | None:
        owner = self._owner()
        for sub in iter_pipes(stage):
            name = type(sub).__name__
            if sub.comm is None:
                return f"{name} is closed; use a new pipe"
            other = sub._owner()
            if other is None:
                continue
            if other is owner:
                return f"{name} is part of the current pipe; use a new pipe"
            where = "an open diagram" if owner is None else "another diagram"
            return f"{name} belongs to {where}; use a new pipe"
        return None

    @T.observe("pipes")
    def _restage(self, change: T.Bunch) -> None:
        owner = self._owner()
        if owner is not None:
            owner._restage(change.old or [], change.new)

    @T.observe("pipes", "inlet")
    def _update_pipes(self, change=None):
        self._stages = tuple(self.pipes)
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
