# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import re
import weakref
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar, TypeVar

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..util import close_widget
from .marks import MarkElementWidget
from .util import resync_stale, settle

AnyWidget = TypeVar("AnyWidget", bound=W.Widget)


class Superseded(Exception):
    """A run gave way to a newer request at a stage boundary.

    Raised by ``Pipeline`` between stages, never inside one, and caught by
    ``Pipe._serve_requests``, which then serves the newer request.
    """


class PipeDisposition(Enum):
    waiting = "waiting"
    running = "running"
    done = "finished"
    error = "error"


@dataclass(frozen=True, eq=False)
class PipeStatus:
    """An immutable snapshot of a pipe's disposition.

    A plain value, not a widget, so replacing ``Pipe.status`` opens no comm.
    Instances compare by identity: assigning a new one always notifies
    ``status`` observers.
    """

    disposition: PipeDisposition = PipeDisposition.done
    elapsed: timedelta | None = None
    exception: BaseException | None = None

    STEPS: ClassVar[dict[PipeDisposition, float]] = {
        PipeDisposition.waiting: 0,
        PipeDisposition.running: 0.5,
        PipeDisposition.done: 1,
        PipeDisposition.error: 1,
    }

    STATES: ClassVar[dict[PipeDisposition, str]] = {
        PipeDisposition.waiting: "",
        PipeDisposition.running: "running",
        PipeDisposition.done: "ok",
        PipeDisposition.error: "error",
    }

    @classmethod
    def waiting(cls) -> PipeStatus:
        return cls(disposition=PipeDisposition.waiting)

    @classmethod
    def running(cls) -> PipeStatus:
        return cls(disposition=PipeDisposition.running)

    @classmethod
    def finished(cls, start_time: datetime | None = None) -> PipeStatus:
        return cls(
            disposition=PipeDisposition.done,
            elapsed=datetime.now() - start_time if start_time else None,
        )

    @classmethod
    def error(cls, start_time: datetime, exception: BaseException) -> PipeStatus:
        return cls(
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
    html: ipywidgets.HTML
        built status HTML to display

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

    def close(self):
        html = self._trait_values.get("html")
        if html is not None:
            close_widget(html)
        super().close()


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
    inlet = T.Instance(MarkElementWidget)
    outlet = T.Instance(MarkElementWidget)
    observes: tuple[str, ...] = TypedTuple(T.Unicode(), kw={})
    reports: tuple[str, ...] = TypedTuple(T.Unicode(), kw={})
    on_progress = T.Callable(default_value=None, allow_none=True)
    on_error = T.Callable(default_value=None, allow_none=True)
    #: the runner serving pending requests; resolves after the trailing run
    _task: asyncio.Task | None = None
    #: ``_generation < _requested`` means a newer request is pending
    _generation: int = 0
    #: the diagram that owns this pipe (see ``Diagram.pipe``)
    _diagram: weakref.ref | None = None
    _requested: int = 0
    status = T.Instance(PipeStatus, kw={})
    status_widget = T.Instance(W.DOMWidget, allow_none=True)

    def __init__(self, *args, **kwargs):
        #: widgets this pipe created, closed with it
        self._owned: list[W.Widget] = []
        super().__init__(*args, **kwargs)

    def _own(self, widget: AnyWidget) -> AnyWidget:
        self._owned.append(widget)
        if isinstance(widget, MarkElementWidget):
            self._owned.append(widget.index)
        return widget

    def _new_mark(self) -> MarkElementWidget:
        return self._own(MarkElementWidget())

    @T.default("inlet")
    def _default_inlet(self):
        return self._new_mark()

    @T.default("outlet")
    def _default_outlet(self):
        return self._new_mark()

    @T.default("status_widget")
    def _default_status_widget(self):
        widget = PipeStatusView()

        def update(change: T.Bunch | None = None):
            widget.update(self)

        update()
        self.observe(update, "status")
        return self._own(widget)

    def close(self):
        """Cancel and close this pipe and the widgets it created.

        An inlet or outlet it was given, such as the source it was connected
        to, is left open.
        """
        self.cancel()
        owned, self._owned = self._owned, []
        for widget in owned:
            close_widget(widget)
        super().close()
        layout = self._trait_values.get("layout")
        if layout is not None:
            layout.close()

    def _repr_mimebundle_(self, **kwargs):
        if self.status_widget is None:
            raise NotImplementedError
        return self.status_widget._repr_mimebundle_(**kwargs)

    def schedule_run(self, change: T.Bunch | None = None) -> asyncio.Task | None:
        """Request a run and return the task that will serve it.

        Requests coalesce on the trailing edge: one runner task serves every
        request made while it is alive, so ten calls in one tick cost one run and
        a call made mid-run costs one more run after it. Nothing is cancelled
        here (see ``cancel``); a ``Pipeline`` gives way at its next stage
        boundary (``Superseded``).

        A runner on another event loop (a kernel subshell, see ``util.settle``)
        is handed over to a new runner on the caller's loop, so the returned task
        is always awaitable by the caller. Pending requests survive the hand-over.

        Returns ``None`` (and schedules nothing) when no event loop is running,
        e.g. when a diagram is built in a plain script or a test: there is no
        loop to run the task on, so raising would only crash widget
        construction (``Diagram(source=...)`` refreshes from a trait observer).
        The request still counts and is served by the next runner.
        """
        self._requested += 1
        task = self._task
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            if task is not None and not task.done():
                return task
            self.log.debug("No running event loop; not scheduling %s", type(self))
            self._task = None
            return None
        if task is not None and not task.done():
            if task.get_loop() is loop:
                return task
            self.log.debug(
                "%s runner lives on another event loop; handing over",
                type(self).__name__,
            )
            self.cancel()
        self._task = task = loop.create_task(self._serve_requests())
        task.add_done_callback(self._post_run)
        return task

    def superseded(self) -> bool:
        """Whether a newer request arrived while the runner's current run is in
        flight (a ``Pipeline`` checks this between stages).
        """
        task = self._task
        return (
            task is not None and not task.done() and self._generation < self._requested
        )

    async def _serve_requests(self) -> None:
        """The runner: run until no request newer than the last run is pending.

        ``on_error`` and ``status`` (via ``_post_run``) reflect the runner's
        *final* outcome, not every run: a run that fails while a newer request
        is pending is logged at WARNING and the newer request is served, so
        only the trailing run's failure reaches ``on_error``.

        The loop yields between runs: a ``run`` that never really awaits and
        requests again from inside itself would otherwise spin without the
        event loop turning.
        """
        served = False
        while self._generation < self._requested:
            if served:
                await asyncio.sleep(0)
            served = True
            self._generation = self._requested
            try:
                await self.run()
            except Superseded:
                self.log.debug("%s gave way to a newer request", type(self).__name__)
            except Exception:
                if not self.superseded():
                    raise
                self.log.warning(
                    "%s run failed; serving the newer request",
                    type(self).__name__,
                    exc_info=True,
                )

    def cancel(self) -> bool:
        """Cancel the runner and drop its pending requests; ``True`` if one was alive.

        The only thing that cancels a run. Use it when the pipe is detached, so
        an in-flight answer is not persisted into an index nobody views. A task
        on another loop is cancelled through that loop (see ``util.settle``).
        """
        task, self._task = self._task, None
        if task is None or task.done():
            return False
        loop = task.get_loop()
        try:
            on_own_loop = asyncio.get_running_loop() is loop
        except RuntimeError:
            on_own_loop = False
        if on_own_loop:
            task.cancel()
        else:
            loop.call_soon_threadsafe(task.cancel)
        return True

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

    def check_dirty(self, flow: tuple[str, ...] | None = None) -> bool:
        """Method to test is this pipe should be run given the set of changes.

        :param flow: the changes to test against; defaults to the pending
            ``inlet.flow``
        :return: dirty flag
        :rtype: bool
        """
        if flow is None:
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
    inlet = T.Instance(MarkElementWidget).tag(sync=True, **W.widget_serialization)

    @T.default("inlet")
    def _default_inlet(self):
        return self._new_mark()


class SyncedOutletPipe(Pipe):
    outlet = T.Instance(MarkElementWidget).tag(sync=True, **W.widget_serialization)

    @T.default("outlet")
    def _default_outlet(self):
        return self._new_mark()


class SyncedPipe(SyncedOutletPipe, SyncedInletPipe):
    """Both inlet and value are synced with the browser"""

    #: generation of the last ``run`` request sent to the browser
    _roundtrip_gen: int = 0
    #: whether an unversioned answer (older extension build) was warned about
    _warned_unversioned: bool = False

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
          stops re-sending) instead of retrying or timing out. Only an error for
          the pending generation (``gen``), or one with no ``gen`` from an older
          extension build, rejects it.
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
            if future is None or future.done():
                return
            gen = content.get("gen")
            if gen is not None and gen != self._roundtrip_gen:
                self.log.debug(
                    "%s ignoring a browser error for generation %s while "
                    "waiting for %s: %s",
                    type(self).__name__,
                    gen,
                    self._roundtrip_gen,
                    content.get("error"),
                )
                return
            settle(
                future,
                "set_exception",
                RuntimeError(str(content.get("error", "browser pipe failed"))),
            )
        elif action == "stale":
            resync_stale(self, self.inlet, self.outlet, missing=content.get("missing"))
