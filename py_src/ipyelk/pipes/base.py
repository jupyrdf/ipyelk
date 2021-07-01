# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import asyncio
import re
from datetime import timedelta
from enum import Enum
from typing import Callable, Optional, Tuple

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .marks import MarkElementWidget


class PipeDisposition(Enum):
    waiting = "waiting"
    running = "running"
    done = "finished"
    error = "error"


STEP = {
    PipeDisposition.waiting: 0,
    PipeDisposition.running: 0.5,
    PipeDisposition.done: 1,
}

STATUS = {
    PipeDisposition.waiting: "",
    PipeDisposition.running: "running",
    PipeDisposition.done: "ok",
    PipeDisposition.error: "error",
}


def rep_elapsed(delta: Optional[timedelta]):
    if not delta:
        return ""
    seconds = delta.total_seconds()
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return "%dd%dh%dm%ds" % (days, hours, minutes, seconds)
    elif hours > 0:
        return "%dh%dm%ds" % (hours, minutes, seconds)
    elif minutes > 0:
        return "%dm%ds" % (minutes, seconds)
    elif seconds >= 1:
        return f"{seconds:.2g}s"
    else:
        return f"{seconds*1000:.3g}ms"


def rep_err(self):
    if not self.exception:
        return ""
    return str(self.exception)


class PipeStatusView(W.VBox):
    include_exception = T.Bool(default_value=False)
    html: W.HTML = T.Instance(W.HTML, kw={})

    @property
    def badge(self):
        r = 10
        margin = 2
        return (
            '<svg viewBox="{box}">'
            '<circle cx="{r}" cy="{r}" r="{r}"></circle>'
            "</svg>"
        ).format(
            box=f"{-margin} {-margin} {2*r+2*margin} {2*r+2*margin}",
            r=r,
        )

    def update_children(self, pipe: "Pipe"):
        self.children = [self.html]

    def update(self, pipe: "Pipe"):
        error = ""
        if self.include_exception and pipe.exception:
            error = (
                '<span class="elk-pipe-error">'
                f"<code>{rep_err(pipe)}</code>"
                '<span class="elk-pipe-accessor">.error()</span>'
                "</span>"
            )

        value = (
            '<pre title="{title}" class="{css_cls}"></span>'
            '<span class="elk-pipe-badge">{badge}</span>'
            '<span class="elk-pipe-elapsed">{elapsed}</span>'
            '<span class="elk-pipe-status">{status}</span>'
            '<span class="elk-pipe-name">{name}</span>'
            "{error}"
            "</pre>"
        ).format(
            badge=self.badge,
            elapsed=rep_elapsed(pipe.elapsed),
            status=STATUS.get(pipe.disposition),
            name=pipe.__class__.__name__,
            title=pipe.__class__,
            css_cls=f"elk-pipe elk-pipe-disposition-{pipe.disposition.value}",
            error=error,
        )
        self.html.value = value
        self.update_children(pipe)


class Pipe(W.Widget):
    disposition = T.Instance(PipeDisposition, default_value=PipeDisposition.done)
    enabled: bool = T.Bool(default_value=True)
    inlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    outlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    dirty: bool = T.Bool(default_value=True)
    observes: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    reports: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    on_progress: Optional[Callable] = T.Any(allow_none=True)
    exception = T.Instance(Exception, allow_none=True)
    _task: asyncio.Future = None
    _dom_widget: W.DOMWidget = T.Instance(W.DOMWidget, allow_none=True)
    elapsed: Optional[timedelta] = T.Instance(timedelta, allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @T.default("_dom_widget")
    def _default_dom_widget(self):
        widget = PipeStatusView()

        def update(change=None):
            widget.update(self)

        update()
        self.observe(update, ("disposition", "exception"))
        return widget

    def _ipython_display_(self, **kwargs):
        if self._dom_widget is None:
            raise NotImplementedError()
        return self._dom_widget._ipython_display_(**kwargs)

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

    def status_update(
        self,
        disposition: PipeDisposition,
        *,
        exception: Exception = None,
        pipe: Optional["Pipe"] = None,
        elapsed: Optional[timedelta] = None,
    ):
        if isinstance(pipe, Pipe):
            pipe.status_update(
                disposition=disposition, exception=exception, elapsed=elapsed
            )
        self.elapsed = elapsed
        self.disposition = disposition

        if exception:
            self.exception = exception

        if callable(self.on_progress):
            self.on_progress(self)

    def get_progress_value(self) -> float:
        return STEP.get(self.disposition, 0)

    def error(self):
        if self.exception:
            raise self.exception


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
