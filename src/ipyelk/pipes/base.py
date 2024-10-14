# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
import re
from datetime import datetime, timedelta
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


class PipeStatus(W.Widget):
    disposition = T.Instance(PipeDisposition, default_value=PipeDisposition.done)
    elapsed: Optional[timedelta] = T.Instance(timedelta, allow_none=True)
    exception = T.Instance(Exception, allow_none=True)
    _task: asyncio.Future = None

    STEPS = {
        PipeDisposition.waiting: 0,
        PipeDisposition.running: 0.5,
        PipeDisposition.done: 1,
    }

    STATES = {
        PipeDisposition.waiting: "",
        PipeDisposition.running: "running",
        PipeDisposition.done: "ok",
        PipeDisposition.error: "error",
    }

    @classmethod
    def waiting(cls):
        return PipeStatus(disposition=PipeDisposition.waiting)

    @classmethod
    def running(cls):
        return PipeStatus(disposition=PipeDisposition.running)

    @classmethod
    def finished(cls, start_time: Optional[datetime] = None):
        return PipeStatus(
            disposition=PipeDisposition.done,
            elapsed=datetime.now() - start_time if start_time else None,
        )

    @classmethod
    def error(cls, start_time: datetime, exception: Exception):
        return PipeStatus(
            disposition=PipeDisposition.error,
            elapsed=datetime.now() - start_time,
            exception=exception,
        )

    def step(self) -> float:
        return self.STEPS.get(self.disposition)

    def state(self) -> str:
        return self.STATES.get(self.disposition)

    def dirty(self) -> bool:
        return self.disposition == PipeDisposition.waiting


def rep_elapsed(delta: Optional[timedelta]):
    if not delta:
        return ""
    seconds = delta.total_seconds()
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return "%dd%dh%dm%ds" % (days, hours, minutes, seconds)
    if hours > 0:
        return "%dh%dm%ds" % (hours, minutes, seconds)
    if minutes > 0:
        return "%dm%ds" % (minutes, seconds)
    if seconds >= 1:
        return f"{seconds:.2g}s"
    return f"{seconds * 1000:.3g}ms"


class PipeStatusView(W.VBox):
    """Widget to display the pipe status.

    Attributes
    ----------
    include_exception: bool
        exception captured
    html: string
        built status html to display

    """

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
            box=f"{-margin} {-margin} {2 * r + 2 * margin} {2 * r + 2 * margin}",
            r=r,
        )

    def update_children(self, pipe: "Pipe"):
        self.children = [self.html]

    def update(self, pipe: "Pipe"):
        """Method to update the status given changes in the pipe."""
        error = ""
        status = pipe.status
        if self.include_exception and status.exception:
            error = (
                '<span class="elk-pipe-error">'
                f"<code>{status.exception}</code>"
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
            elapsed=rep_elapsed(status.elapsed),
            status=status.state(),
            name=pipe.__class__.__name__,
            title=pipe.__class__,
            css_cls=f"elk-pipe elk-pipe-disposition-{status.disposition.value}",
            error=error,
        )
        self.html.value = value
        self.update_children(pipe)


class Pipe(W.Widget):
    """A step in the processing pipeline for diagrams.

    Attributes
    ----------
    inlet: :py:class:`~ipyelk.pipes.MarkElementWidget`
        input elements to manipulate.
    outlet: :py:class:`~ipyelk.pipes.MarkElementWidget`
        output elements that potentially have been manipulated.
    observed: tuple of :py:class:`~str`
        which potential changes that would require this pipe to be rerun.
    reports: tuple of :py:class:`~str`
        types of changes that get added to the output based of rerunning this
        pipe.
    on_progress: :py:class:`~callable`
        Callable function that is executed when the pipe is running.
    status: :py:class:`~ipyelk.pipes.base.PipeStatus`
        Captures the disposition of the pipe during the change lifecycle.
    status_view: :py:class:`~ipyelk.pipes.base.PipeStatusView`
        Widget to show pipe status as it updates.
    enabled: bool
        whether the processing step can be run

    """

    enabled: bool = T.Bool(default_value=True)
    inlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    outlet: MarkElementWidget = T.Instance(MarkElementWidget, kw={})
    observes: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    reports: Tuple[str] = TypedTuple(T.Unicode(), kw={})
    on_progress: Optional[Callable] = T.Any(allow_none=True)
    _task: asyncio.Future = None
    status: PipeStatus = T.Instance(PipeStatus, kw={})
    status_widget: W.DOMWidget = T.Instance(W.DOMWidget, allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @T.default("status_widget")
    def _default_status_widget(self):
        widget = PipeStatusView()

        def update(change=None):
            widget.update(self)

        update()
        self.observe(update, "status")
        return widget

    def _repr_mimebundle_(self, **kwargs):
        if self.status_widget is None:
            raise NotImplementedError
        return self.status_widget._repr_mimebundle_(**kwargs)

    def schedule_run(self, change: T.Bunch = None) -> asyncio.Task:
        """Schedule rerunning the pipe on the event loop."""
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
        """Run method that takes the input performs checks/changes, and sets the
        output value.

        Subclasses of the pipe will implement their own custom processing logic.
        """
        # do work
        self.outlet.value = self.inlet.value

    def check_dirty(self) -> bool:
        """Method to test is this pipe should be run given the set of changes.

        :return: dirty flag
        :rtype: bool
        """
        flow = self.inlet.flow

        if any(any(re.match(f"^{obs}$", f) for f in flow) for obs in self.observes):
            # mark this pipe as dirty so will run
            self.status = PipeStatus.waiting()
            # add this pipes reporting to the outlet flow
            flow = tuple(set([*flow, *self.reports]))
        else:
            self.status = PipeStatus.finished()
        self.outlet.flow = flow
        return self.status.dirty()

    def status_update(
        self,
        status: PipeStatus,
        pipe: Optional["Pipe"] = None,
    ):
        if isinstance(pipe, Pipe):
            pipe.status_update(status=status)
        self.status = status

        if callable(self.on_progress):
            self.on_progress(self)

    def get_progress_value(self) -> float:
        return self.status.step()

    def error(self):
        """Method to raise any potential errors captured during the running of
        the pipe.

        :raises self.status.exception: captured exception during the processing.
        """
        if self.status.exception:
            raise self.status.exception


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
