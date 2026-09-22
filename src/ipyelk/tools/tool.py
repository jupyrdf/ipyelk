# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
from collections.abc import Iterator

import ipywidgets as W
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..exceptions import (
    DeprecatedAPIError,
    RegistrationMethod,
    RemovedAPI,
    check_removed,
)
from ..pipes import Pipe

_REGISTRATION_ASSIGNED = (
    "Tool.{name} is a registration method in ipyelk 3.0, not an assignable "
    "callable: a single slot let one assignment silently replace another "
    "listener's callback (the Diagram registers its own refresh on on_done). "
    "Register tool.{name}(callback) (called as callback(tool); remove=True "
    "unregisters). This error is raised throughout 3.x."
)
#: the registration methods; assigning or passing them as constructor keywords raises
_REGISTRATION_METHODS = ("on_start", "on_done")


class Tool(W.Widget):
    """An interactive element to control a diagram.

    Execution lifecycle
    -------------------
    * :meth:`trigger` requests execution: it cancels a still-running request,
      schedules :meth:`run` as an :class:`asyncio.Task` and returns it. A tool that
      does not implement ``run()`` (state-only tools such as
      :py:class:`~ipyelk.tools.Selection`, or callback tools such as
      :py:class:`~ipyelk.tools.ToolButton`) rejects the request with
      ``NotImplementedError`` before anything is scheduled.
    * :meth:`run` performs the work.
    * ``on_start`` callbacks (registered with :meth:`on_start`) fire with the tool as
      their argument when the work actually starts, i.e. when the task first runs
      -- not when :meth:`trigger` is called, and never for a rejected request.
    * :attr:`reports` are recorded on the attached pipe (:meth:`record_reports`)
      once the work has started and finishes -- successfully, with an error, or
      cancelled -- so partial changes from failed or cancelled work still reach
      the next refresh. Recording merges; it never drops another writer's reports.
    * ``on_done`` callbacks (registered with :meth:`on_done`) fire with the tool as
      their argument **only after run() completes successfully and its change
      reports are recorded**. They never fire when execution fails, is cancelled,
      or is rejected before starting. Errors are logged.
    * A request that was superseded by a newer :meth:`trigger` is stale: its
      completion records its reports and, when it succeeded, still fires
      ``on_done``, but it never touches the tool's task state, which the newer
      request owns.

    Both hooks are registration methods -- ``tool.on_start(callback)``,
    ``tool.on_done(callback)`` -- so several listeners (the owning
    :py:class:`~ipyelk.diagram.Diagram` registers its refresh on ``on_done``) can
    coexist. Assigning ``tool.on_start = callback`` or ``tool.on_done = callback``
    (the 2.x single-slot form) is an error.
    """

    tee = T.Instance(Pipe, allow_none=True).tag(sync=True, **W.widget_serialization)
    disabled = T.Bool(
        default_value=False,
        help="an execution guard: trigger() and button clicks are rejected, and every "
        "control under ``ui`` that has a ``disabled`` trait is disabled",
    )
    reports = TypedTuple(T.Unicode(), kw={})
    _task: asyncio.Task | None = None
    ui = T.Instance(W.DOMWidget, allow_none=True)
    priority = T.Int(default_value=10)
    _on_start_handlers = T.Instance(W.CallbackDispatcher, kw={})
    _on_done_handlers = T.Instance(W.CallbackDispatcher, kw={})
    #: names of ``Instance(..., allow_none=True)`` traits a subclass needs bound before
    #: it can run. A tool with any of them still ``None`` is *unbound*: it can be
    #: constructed and bound later (``Diagram.register_tool``), its controls are
    #: disabled meanwhile, and ``trigger()`` rejects it with a ``RuntimeError`` naming
    #: the missing dependency.
    _dependencies: tuple[str, ...] = ()

    #: removed names raise :class:`~ipyelk.exceptions.DeprecatedAPIError` through 3.x
    handler = RemovedAPI(
        "Tool.handler was removed in ipyelk 3.0. It was three different things "
        "(the execution method, ToolButton's click callback trait, and SetTool's "
        "trait observer). Call tool.trigger() to request execution; pass "
        "ToolButton(on_click=callback) for a button callback (called as "
        "callback(tool))."
    )
    on_run = RemovedAPI(
        "Tool.on_run was removed in ipyelk 3.0. Despite its name, on_run callbacks "
        "ran AFTER a successful run, not when the run started, so the name was "
        "ambiguous. Register tool.on_start(callback) for the actual start of the "
        "work, or tool.on_done(callback) for success only (both are called as "
        "callback(tool); on_done never fires on failure, cancellation, or a "
        "rejected trigger). No forwarding: this error is raised throughout 3.x."
    )
    disable = RemovedAPI(
        "Tool.disable was removed in ipyelk 3.0: nothing read it, so it never disabled "
        "anything. Use tool.disabled (the ipywidgets name), which rejects trigger() "
        "and clicks and disables the controls under tool.ui."
    )

    def __init__(self, **kwargs: object):
        check_removed(type(self), kwargs)
        for name in _REGISTRATION_METHODS:
            if name in kwargs:
                raise DeprecatedAPIError(_REGISTRATION_ASSIGNED.format(name=name))
        super().__init__(**kwargs)
        if self._dependencies:
            self.observe(self._update_controls, list(self._dependencies))

    def trigger(self, *_: object) -> asyncio.Task:
        """Request execution: schedule :meth:`run` and return its task.

        Positional arguments are ignored so the method can be an ipywidgets
        callback (``button.on_click(tool.trigger)``). Raises before scheduling
        anything when the request is rejected (see the class docstring).
        """
        if type(self).run is Tool.run:
            raise NotImplementedError(
                f"{type(self).__name__} does not implement run(): it is a state-only "
                "or callback tool, so there is nothing for trigger() to schedule"
            )
        self.check_enabled()
        # cancel old work if needed
        if self._task is not None:
            self._task.cancel()

        # schedule work
        self._task = asyncio.create_task(self._execute())
        self._task.add_done_callback(self._finished)
        return self._task

    async def run(self):
        raise NotImplementedError

    def missing_dependencies(self) -> tuple[str, ...]:
        """The ``_dependencies`` that are still ``None``; empty when the tool is bound."""
        return tuple(n for n in self._dependencies if getattr(self, n) is None)

    def check_enabled(self) -> None:
        """Raise ``RuntimeError`` if an invocation must be rejected right now."""
        name = type(self).__name__
        if self.disabled:
            raise RuntimeError(f"{name} is disabled")
        missing = self.missing_dependencies()
        if missing:
            raise RuntimeError(
                f"{name} is not bound: {', '.join(missing)} is None. Pass it at "
                "construction, assign it, or add the tool with Diagram.register_tool()"
            )

    def _controls_disabled(self) -> bool:
        return self.disabled or bool(self.missing_dependencies())

    @T.observe("disabled", "ui")
    def _update_controls(self, change: T.Bunch | None = None) -> None:
        for control in _controls(self.ui):
            control.disabled = self._controls_disabled()

    @T.observe("ui", type="default")
    def _update_default_ui_controls(self, change: T.Bunch) -> None:
        # the lazily built default ``ui`` emits a "default" event, not a "change"
        for control in _controls(change.value):
            control.disabled = self._controls_disabled()

    async def _execute(self) -> None:
        self._on_start_handlers(self)
        try:
            await self.run()
        finally:
            # success, error or cancellation: the work may have changed the model
            self.record_reports()

    def record_reports(self) -> None:
        """Mark this tool's ``reports`` as pending on the attached pipe.

        The inlet flow is the set of pending reports every writer (tools, the
        diagram, the pipeline itself) shares; a pending report is a request some
        writer already made and this tool cannot know whether it was satisfied.
        The reports are therefore merged into the flow -- order preserved,
        duplicates dropped -- never assigned over it. No-op without a ``tee``.
        """
        if self.tee is None:
            return
        inlet = self.tee.inlet
        inlet.flow = tuple(dict.fromkeys((*inlet.flow, *self.reports)))

    def on_start(self, callback, remove=False):
        """Register a callback for when this tool's work actually starts.

        The callback is called with one argument, the tool. It does not fire for
        a request rejected by :meth:`trigger`.

        Parameters
        ----------
        remove: bool (optional)
            set to true to remove the callback from the list of callbacks.

        """
        self._on_start_handlers.register_callback(callback, remove=remove)

    on_start = RegistrationMethod(
        on_start, _REGISTRATION_ASSIGNED.format(name="on_start")
    )

    def on_done(self, callback, remove=False):
        """Register a callback for when this tool's work succeeded.

        The callback is called with one argument, the tool, **only after run()
        completed successfully and its change reports were recorded** -- never on
        failure, cancellation, or a request rejected by :meth:`trigger`.

        Parameters
        ----------
        remove: bool (optional)
            set to true to remove the callback from the list of callbacks.

        """
        self._on_done_handlers.register_callback(callback, remove=remove)

    on_done = RegistrationMethod(on_done, _REGISTRATION_ASSIGNED.format(name="on_done"))

    def _finished(self, task: asyncio.Task):
        if task is self._task:
            self._task = None  # else stale: a newer request owns the task state
        try:
            task.result()
        except asyncio.CancelledError:
            return  # cancellation should not log an error
        except Exception:
            self.log.exception(f"Error running tool: {type(self)}")
            return
        # every success fires, stale or not: a stale success is still a finished
        # run whose reports the listeners (the Diagram's refresh) must see
        self._on_done_handlers(self)


class ToolButton(Tool):
    """Generic Tool that provides a simple button UI.

    Clicking the button calls ``on_click(tool)`` synchronously; a ``ToolButton``
    has no ``run()`` and does not use the :meth:`~Tool.trigger` lifecycle.

    :param on_click: Called as ``on_click(tool)`` when the button is pressed.
    """

    on_click = T.Callable(default_value=None, allow_none=True)
    description = T.Unicode(default_value="")

    @T.default("ui")
    def _default_ui(self):
        btn = W.Button(description=self.description)
        T.link((self, "description"), (btn, "description"))

        def click(*args):
            self.check_enabled()
            if callable(self.on_click):
                self.on_click(self)

        btn.on_click(click)
        return btn


def _controls(widget: W.Widget | None) -> Iterator[W.Widget]:
    """The widgets under ``widget`` (itself included) that have a ``disabled`` trait.

    Not every DOMWidget can be disabled (boxes, progress bars): those are walked
    through, not disabled.
    """
    if widget is None:
        return
    if widget.has_trait("disabled"):
        yield widget
    for child in getattr(widget, "children", ()):
        yield from _controls(child)
