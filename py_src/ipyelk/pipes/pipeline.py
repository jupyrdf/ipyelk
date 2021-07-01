# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from datetime import datetime
from typing import Tuple

import ipywidgets as W
import traitlets as T

from ..exceptions import BrokenPipe
from .base import Pipe, PipeDisposition, PipeStatusView, SyncedOutletPipe


class PipelineStatusView(PipeStatusView):

    toggle_btn = T.Instance(W.Button)
    include_exception = T.Bool(default_value=True)
    collapsed = T.Bool(default_value=True)
    statuses = T.List()

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
            W.HBox(
                [
                    self.toggle_btn,
                    self.html,
                ]
            ),
        ]
        if not self.collapsed:
            children.extend(self.statuses)
        self.children = children

    def update_children(self, pipe: "Pipeline"):
        statuses = [p._dom_widget for p in pipe.pipes]
        self.statuses = [
            W.HBox(
                [
                    W.HTML(value="<pre>  </pre>").add_class("elk-pipe-space"),
                    status,
                    W.HTML(value=f'<pre class="elk-pipe-accessor">.pipes[{i}]</pre>'),
                ]
            )
            for i, status in enumerate(statuses)
        ]


class Pipeline(SyncedOutletPipe):
    pipes: Tuple[Pipe] = T.List(T.Instance(Pipe), kw={}).tag(
        sync=True, **W.widget_serialization
    )

    @T.default("_dom_widget")
    def _default_dom_widget(self):
        widget = PipelineStatusView()

        def update(change=None):
            widget.update(self)

        update()
        self.observe(update, ("disposition", "exception"))
        return widget

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
        start = datetime.now()
        # Clear exceptions and run time
        for pipe in [self, *self.pipes]:
            pipe.exception = None
            pipe.elapsed = None
        self.check_dirty()

        # Look at enabled pipes
        for i, pipe in enumerate(self.pipes):
            # TODO use i and num_steps for reporting processing stage
            start_time = datetime.now()
            p_name = f"pipe {i}: {type(pipe)}"
            if pipe.dirty:
                self.status_update(PipeDisposition.running, pipe=pipe)
                try:

                    await pipe.run()
                except Exception as err:
                    self.log.exception(f"Error running {p_name}")
                    end_time = datetime.now()
                    self.status_update(
                        PipeDisposition.error,
                        exception=err,
                        pipe=pipe,
                        elapsed=end_time - start_time,
                    )
                    raise err
                pipe.dirty = False
            else:
                pipe.outlet.value = pipe.inlet.value
            end_time = datetime.now()
            pipe.status_update(PipeDisposition.done, elapsed=end_time - start_time)

        self.dirty = False
        self.status_update(PipeDisposition.done, elapsed=end_time - start)

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

        self.observes = tuple(observes)
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

    def get_progress_value(self) -> float:
        return sum(pipe.get_progress_value() for pipe in self.pipes) / len(self.pipes)
