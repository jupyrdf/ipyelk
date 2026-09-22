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


class Superseded(Exception):
    """A run gave way to a newer request at a stage boundary.

    Raised by ``Pipeline`` between stages when ``Pipe.schedule_run`` was
    called while the run was in flight; caught by the runner
    (``Pipe._serve_requests``), which then serves the newer request.  Never
    raised inside a stage: a browser roundtrip that was sent is always
    awaited to its answer, error or timeout.
    """


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
    #: the runner serving the pending requests (see ``schedule_run``); it
    #: resolves after the *trailing* run, so ``await pipe._task`` waits for
    #: every request made while it was alive
    _task: asyncio.Task | None = None
    #: request counters: ``schedule_run`` bumps ``_requested``; the runner
    #: stamps ``_generation`` when it starts a run, so ``_generation <
    #: _requested`` means a newer request is pending
    _generation: int = 0
    _requested: int = 0
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
        """Request a run and return the task that will serve it.

        Requests coalesce on the trailing edge: one *runner* task serves every
        request made while it is alive, running ``run`` again until no newer
        request is pending, so ten calls in one tick cost one run and a call
        made mid-run costs one more run *after* the current one.  Nothing is
        cancelled here -- a browser roundtrip that was sent is always awaited
        (``cancel`` is the explicit way to stop a run); a ``Pipeline`` instead
        gives way at its next stage boundary (``Superseded``).

        Returns ``None`` (and schedules nothing) when no event loop is running,
        e.g. when a diagram is built in a plain script or a test: there is no
        loop to run the task on, so raising would only crash widget
        construction (``Diagram(source=...)`` refreshes from a trait observer).
        The request still counts and is served by the next runner.
        """
        self._requested += 1
        task = self._task
        if task is not None and not task.done():
            return task
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.log.debug("No running event loop; not scheduling %s", type(self))
            self._task = None
            return None
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
                # the failed run is stale anyway; the newer request may well
                # succeed (a ``Pipeline`` has already logged the stage error)
                self.log.warning(
                    "%s run failed; serving the newer request",
                    type(self).__name__,
                    exc_info=True,
                )

    def cancel(self) -> bool:
        """Cancel the runner and drop its pending requests; ``True`` if one was alive.

        This is the only thing that cancels a run: ``schedule_run`` never does.
        Use it when the pipe is detached (``Diagram`` replaces its pipe or
        source) -- an in-flight browser answer would otherwise be persisted
        into an index nobody views.  The next ``schedule_run`` starts a fresh
        runner.
        """
        task, self._task = self._task, None
        if task is None or task.done():
            return False
        task.cancel()
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
            ``inlet.flow``.  A ``Pipeline`` passes the flow it *took* at the
            start of a run to its first pipe (``MarkElementWidget.take``).
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
    inlet = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedOutletPipe(Pipe):
    outlet = T.Instance(MarkElementWidget, kw={}).tag(
        sync=True, **W.widget_serialization
    )


class SyncedPipe(SyncedOutletPipe, SyncedInletPipe):
    """Both inlet and value are synced with the browser"""

    #: generation of the last ``run`` request sent to the browser; the answer
    #: carries it back in ``outlet.gen`` (see ``util.browser_roundtrip``)
    _roundtrip_gen: int = 0
    #: set once this pipe accepted an answer without a generation (an older
    #: extension build); the acceptance is warned about once per pipe
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
          stops re-sending) instead of retrying or timing out.  The report
          carries the generation of the request that failed (``gen``): a late
          error from a generation this pipe abandoned (``cancel``) must not
          kill the roundtrip now pending, so only a matching generation
          rejects; a report without ``gen`` (an older extension build) always
          does.
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
            future.set_exception(
                RuntimeError(str(content.get("error", "browser pipe failed")))
            )
        elif action == "stale":
            resync_stale(self, self.inlet, self.outlet, missing=content.get("missing"))
