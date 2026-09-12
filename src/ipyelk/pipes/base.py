# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from enum import Enum

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .marks import MarkElementWidget
from .util import resync_stale


class PipeDisposition(Enum):
    waiting = "waiting"
    running = "running"
    done = "finished"
    error = "error"


class PipeStatus(W.Widget):
    disposition = T.Instance(PipeDisposition, default_value=PipeDisposition.done)
    elapsed = T.Instance(timedelta, allow_none=True)
    exception = T.Instance(BaseException, allow_none=True)
    _task: asyncio.Future | None = None

    STEPS = {
        PipeDisposition.waiting: 0,
        PipeDisposition.running: 0.5,
        PipeDisposition.done: 1,
        PipeDisposition.error: 1,
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
    def finished(cls, start_time: datetime | None = None):
        return PipeStatus(
            disposition=PipeDisposition.done,
            elapsed=datetime.now() - start_time if start_time else None,
        )

    @classmethod
    def error(cls, start_time: datetime, exception: BaseException):
        return PipeStatus(
            disposition=PipeDisposition.error,
            elapsed=datetime.now() - start_time,
            exception=exception,
        )

    def step(self) -> float:
        return float(self.STEPS[self.disposition])

    def state(self) -> str:
        return self.STATES[self.disposition]

    def dirty(self) -> bool:
        return self.disposition == PipeDisposition.waiting


def rep_elapsed(delta: timedelta | None):
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
    html = T.Instance(W.HTML, kw={})

    @property
    def badge(self):
        r = 10
        margin = 2
        return (
            '<svg viewBox="{box}"><circle cx="{r}" cy="{r}" r="{r}"></circle></svg>'
        ).format(
            box=f"{-margin} {-margin} {2 * r + 2 * margin} {2 * r + 2 * margin}",
            r=r,
        )

    def update_children(self, pipe: Pipe):
        self.children = [self.html]

    def update(self, pipe: Pipe):
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

    enabled = T.Bool(default_value=True)
    inlet = T.Instance(MarkElementWidget, kw={})
    outlet = T.Instance(MarkElementWidget, kw={})
    observes: tuple[str, ...] = TypedTuple(T.Unicode(), kw={})
    reports: tuple[str, ...] = TypedTuple(T.Unicode(), kw={})
    on_progress = T.Callable(default_value=None, allow_none=True)
    on_error = T.Callable(default_value=None, allow_none=True)
    _task: asyncio.Future | None = None
    status = T.Instance(PipeStatus, kw={})
    status_widget = T.Instance(W.DOMWidget, allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @T.default("status_widget")
    def _default_status_widget(self):
        widget = PipeStatusView()

        def update(change: T.Bunch | None = None):
            widget.update(self)

        update()
        self.observe(update, "status")
        return widget

    def _repr_mimebundle_(self, **kwargs):
        if self.status_widget is None:
            raise NotImplementedError
        return self.status_widget._repr_mimebundle_(**kwargs)

    def schedule_run(self, change: T.Bunch | None = None) -> asyncio.Task | None:
        """Schedule rerunning the pipe on the event loop.

        Returns ``None`` (and schedules nothing) when no event loop is running,
        e.g. when a diagram is built in a plain script or a test: there is no
        loop to run the task on, so raising would only crash widget
        construction (``Diagram(source=...)`` refreshes from a trait observer).
        """
        # schedule task on loop
        if self._task:
            self._task.cancel()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.log.debug("No running event loop; not scheduling %s", type(self))
            self._task = None
            return None
        self._task = loop.create_task(self.run())

        self._task.add_done_callback(self._post_run)
        return self._task

    def _post_run(self, future: asyncio.Future):
        try:
            exception = future.exception()
        except asyncio.CancelledError:
            return
        if exception is None:
            return
        if (
            not isinstance(self.status, PipeStatus)
            or self.status.exception is not exception
        ):
            self.status = PipeStatus.error(
                start_time=datetime.now(), exception=exception
            )
        if callable(self.on_error):
            self.on_error(self, exception)

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
        pipe: Pipe | None = None,
    ):
        if isinstance(pipe, Pipe):
            pipe.status_update(status=status)
        self.status = status

        if callable(self.on_progress):
            try:
                self.on_progress(self)
            except Exception:
                self.log.exception(
                    "Error in on_progress callback for %s", type(self).__name__
                )

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

    def __init__(self, *args, **kwargs):
        self._stale_resync_at: float = 0.0
        self._stale_resync_interval: float = 0.0
        super().__init__(*args, **kwargs)
        self.on_msg(self._handle_browser_msg)

    def _handle_browser_msg(
        self, widget: W.Widget, content: dict[str, object], buffers: list[bytes] | None
    ):
        """React to the browser's answers on the pipe's custom-message channel.

        * ``action: error`` -- the frontend failed to produce an outlet value;
          reject the pending roundtrip future so the kernel stops waiting (and
          stops re-sending) instead of retrying or timing out.
        * ``action: stale`` -- the frontend got a ``run`` request it cannot
          serve because state it needs (inlet/outlet wiring, the inlet value)
          never arrived: widget state sync has no retransmit, and
          jupyter-server's iopub rate limiter silently drops ``comm_msg``
          under bursty load. Re-emit the full state of the pipe and its
          endpoints so the ongoing resend loop can converge within its
          ``timeout``; throttled, since the re-sync (three states, the inlet
          value can be large) goes over the same congested channel.
        """
        if not isinstance(content, dict):
            return
        action = content.get("action")
        if action == "error":
            future = getattr(self, "_roundtrip_future", None)
            if future is not None and not future.done():
                future.set_exception(
                    RuntimeError(str(content.get("error", "browser pipe failed")))
                )
        elif action == "stale":
            resync_stale(self, self.inlet, self.outlet, missing=content.get("missing"))
