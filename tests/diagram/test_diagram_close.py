# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Diagram.close()`` closes what the diagram owns (#191)."""

from __future__ import annotations

import asyncio
import gc
import logging
import weakref

import ipywidgets as W
import pytest
import traitlets as T

from ipyelk import Diagram
from ipyelk.diagram import SprottyViewer
from ipyelk.diagram.flow import DefaultFlow
from ipyelk.elements import SymbolSpec
from ipyelk.exceptions import ClosedError
from ipyelk.pipes import (
    BrowserTextSizer,
    ElkJS,
    MarkElementWidget,
    Pipe,
    ValidationPipe,
    VisibilityPipe,
)
from ipyelk.pipes import flows as F
from ipyelk.pipes.pipeline import Pipeline
from ipyelk.tools import ControlOverlay, SetTool, ToggleCollapsedTool, Tool, Toolbar
from ipyelk.util import close_widget

from .test_pipe_replacement import ROUNDS, is_open, live_widgets, make_source, refresh

pytestmark = pytest.mark.usefixtures("headless")


@pytest.fixture
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


async def build_and_close(show_view: bool) -> None:
    source = make_source()
    diagram = Diagram(source=source)
    if show_view:
        assert diagram.pipe.status_widget is not None
    await refresh(diagram)
    diagram.close()
    assert is_open(source)
    close_widget(source)


@pytest.mark.asyncio
@pytest.mark.parametrize("show_view", [False, True], ids=["view-hidden", "view-shown"])
async def test_closing_diagrams_leaves_no_live_widgets(show_view: bool) -> None:
    await build_and_close(show_view)
    before = live_widgets()
    for _ in range(ROUNDS):
        await build_and_close(show_view)
    assert live_widgets() - before == 0


@pytest.mark.asyncio
async def test_close_keeps_the_source_and_what_was_passed_in() -> None:
    source = make_source()
    given = MarkElementWidget()
    pipe = Pipeline(
        pipes=[
            DefaultFlow(
                pipes=[
                    ValidationPipe(),
                    BrowserTextSizer(),
                    VisibilityPipe(),
                    ElkJS(outlet=given),
                ]
            )
        ]
    )
    diagram = Diagram(source=source, pipe=pipe)
    diagram.register_tool(SetTool())
    await refresh(diagram)
    view, toolbar, tools = diagram.view, diagram.toolbar, diagram.tools
    subs = [pipe, *pipe.pipes, *pipe.pipes[0].pipes]
    created = [p.outlet for p in pipe.pipes[0].pipes[:-1]]
    uis = [tool.ui for tool in tools if tool.ui is not None]

    diagram.close()

    assert diagram.closed
    for widget in [*subs, *created, view, toolbar, *tools, *uis]:
        assert not is_open(widget), widget
    for widget in (source, given):
        assert is_open(widget)
    assert diagram.source is source
    assert all(sub._diagram is None for sub in subs)


@pytest.mark.asyncio
async def test_a_closed_diagram_is_collected() -> None:
    diagram = Diagram(source=make_source())
    await refresh(diagram)
    refs = [weakref.ref(w) for w in (diagram, diagram.pipe, diagram.view)]
    diagram.close()
    diagram.close()
    del diagram
    gc.collect()
    assert [ref() for ref in refs] == [None, None, None]


def test_close_keeps_widgets_passed_in() -> None:
    slider, layout, view_layout = W.IntSlider(), W.Layout(), W.Layout()
    overlay = ControlOverlay(children=[W.Button()])
    view = SprottyViewer(layout=view_layout, control_overlay=overlay)
    tool = Tool(ui=W.HBox([slider]))
    diagram = Diagram(source=make_source(), layout=layout, view=view)
    diagram.register_tool(tool)
    built = SetTool()
    diagram.register_tool(built)
    built_ui = [built.ui, *built.ui.children]

    diagram.close()

    assert not is_open(view)
    assert not is_open(tool)
    assert not any(is_open(widget) for widget in built_ui)
    for widget in (slider, tool.ui, layout, view_layout, overlay, *overlay.children):
        assert is_open(widget), widget


def test_a_closed_diagram_drops_its_links_and_callbacks() -> None:
    diagram = Diagram(source=make_source())
    toolbar, view, tools = diagram.toolbar, diagram.view, diagram.tools
    symbols = diagram.symbols
    diagram.close()

    assert all(
        diagram.refresh not in tool._on_done_handlers.callbacks for tool in tools
    )
    toolbar.tools = ()
    assert diagram.tools == tools
    view.symbols = type(symbols)()
    assert diagram.symbols is symbols


ENTRY_POINTS = {
    "refresh": lambda d: d.refresh(),
    "register a tool": lambda d: d.register_tool(SetTool()),
    "set pipe": lambda d: setattr(d, "pipe", DefaultFlow()),
    "set source": lambda d: setattr(d, "source", make_source()),
    "set view": lambda d: setattr(d, "view", SprottyViewer()),
    "set tools": lambda d: setattr(d, "tools", ()),
    "set toolbar": lambda d: setattr(d, "toolbar", Toolbar()),
    "set symbols": lambda d: setattr(d, "symbols", SymbolSpec()),
    "set style": lambda d: setattr(d, "style", {" .a": {"fill": "red"}}),
}
TRAITS = ("pipe", "source", "view", "tools", "toolbar", "symbols", "style")


@pytest.mark.parametrize("action", ENTRY_POINTS)
def test_a_closed_diagram_raises(action: str) -> None:
    diagram = Diagram(source=make_source())
    diagram.close()
    before = {name: getattr(diagram, name) for name in TRAITS}

    msg = f"^Diagram is closed and cannot {action}; build a new Diagram$"
    with pytest.raises(ClosedError, match=msg):
        ENTRY_POINTS[action](diagram)

    assert {name: getattr(diagram, name) for name in TRAITS} == before


def test_closed_is_a_trait_error_and_a_runtime_error() -> None:
    assert issubclass(ClosedError, T.TraitError)
    assert issubclass(ClosedError, RuntimeError)


def test_closed_reports_what_was_closed() -> None:
    diagram = Diagram(source=make_source())
    pipe, stage = diagram.pipe, diagram.pipe.pipes[0]
    assert not any(widget.closed for widget in (diagram, pipe, stage))

    stage.close()
    assert stage.closed
    assert not pipe.closed
    assert not diagram.closed

    diagram.close()
    assert diagram.closed
    assert pipe.closed
    with pytest.raises(AttributeError):
        diagram.closed = False


@pytest.mark.parametrize("owned", [True, False], ids=["diagram-pipe", "standalone"])
def test_a_closed_pipeline_refuses_pipes_and_keeps_them(owned: bool) -> None:
    diagram = Diagram(source=make_source()) if owned else None
    pipe = diagram.pipe if diagram else Pipeline(pipes=[ValidationPipe()])
    stages = list(pipe.pipes)
    (diagram or pipe).close()
    name = type(pipe).__name__
    msg = f"^{name} is closed and cannot set pipes; use a new pipe$"

    for pipes in ([ValidationPipe(), ValidationPipe()], [stages[0]], []):
        with pytest.raises(ClosedError, match=msg):
            pipe.pipes = pipes
        assert pipe.pipes == stages


@pytest.mark.asyncio
@pytest.mark.parametrize("plain", [False, True], ids=["pipeline", "pipe"])
async def test_a_closed_pipeline_refuses_runs(plain: bool) -> None:
    kwargs = {"pipe": Pipe()} if plain else {}
    diagram = Diagram(source=make_source(), **kwargs)
    pipe = diagram.pipe
    pipe.close()
    msg = f"^{type(pipe).__name__} is closed and cannot run; use a new pipe$"

    with pytest.raises(ClosedError, match=msg):
        diagram.refresh()
    with pytest.raises(ClosedError, match=msg):
        pipe.schedule_run()
    if isinstance(pipe, Pipeline):
        with pytest.raises(ClosedError, match=msg):
            await pipe.run()
    assert pipe._task is None
    diagram.close()


def test_closing_twice_is_a_silent_no_op() -> None:
    diagram = Diagram(source=make_source())
    pipe = diagram.pipe
    diagram.close()
    widgets = live_widgets()

    diagram.close()
    pipe.close()

    assert live_widgets() == widgets
    assert diagram.closed


class Closer(Pipe):
    """A stage that calls ``hook`` and lets the run go on."""

    hook = None

    async def run(self):
        self.hook()
        self.outlet.value = self.inlet.value


@pytest.mark.asyncio
@pytest.mark.parametrize("closing", ["pipeline", "diagram"])
async def test_closing_mid_run_cancels_before_a_nested_stage(
    closing: str, caplog: pytest.LogCaptureFixture
) -> None:
    closer = Closer(observes=(F.New,))
    nested = Pipeline(pipes=[Pipe(observes=(F.New,), reports=(F.Layout,))])
    pipe = Pipeline(pipes=[closer, nested])
    errors = []
    pipe.on_error = lambda _pipe, error: errors.append(error)
    diagram = Diagram(source=make_source(), pipe=pipe)
    closer.hook = pipe.close if closing == "pipeline" else diagram.close

    task = diagram.refresh()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert task.cancelled()
    assert errors == []
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
    diagram.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("closing", ["pipeline", "diagram"])
async def test_closing_from_progress_cancels_before_a_nested_stage(
    closing: str, caplog: pytest.LogCaptureFixture
) -> None:
    nested = Pipeline(pipes=[Pipe(observes=(F.New,), reports=(F.Layout,))])
    pipe = Pipeline(pipes=[nested])
    errors = []
    pipe.on_error = lambda _pipe, error: errors.append(error)
    diagram = Diagram(source=make_source(), pipe=pipe)
    pipe.on_progress = lambda _pipe: (
        pipe.close() if closing == "pipeline" else diagram.close()
    )

    try:
        task = diagram.refresh()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
        assert errors == []
        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
    finally:
        diagram.close()


class Counting(Pipe):
    """A stage that counts its runs."""

    runs = 0

    async def run(self):
        self.runs += 1
        self.outlet.value = self.inlet.value


@pytest.mark.asyncio
@pytest.mark.parametrize("closing", ["pipeline", "diagram"])
async def test_closing_from_progress_skips_a_plain_stage(
    closing: str, caplog: pytest.LogCaptureFixture
) -> None:
    stage = Counting(observes=(F.New,), reports=(F.Layout,))
    pipe = Pipeline(pipes=[stage])
    errors = []
    pipe.on_error = lambda _pipe, error: errors.append(error)
    diagram = Diagram(source=make_source(), pipe=pipe)
    pipe.on_progress = lambda _pipe: (
        pipe.close() if closing == "pipeline" else diagram.close()
    )

    try:
        task = diagram.refresh()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
        assert stage.runs == 0
        assert errors == []
        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
    finally:
        diagram.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("closing", ["pipeline", "diagram"])
async def test_closing_from_the_last_stages_finished_update_cancels(
    closing: str,
) -> None:
    stage = Counting(observes=(F.New,), reports=(F.Layout,))
    pipe = Pipeline(pipes=[stage])
    errors = []
    pipe.on_error = lambda _pipe, error: errors.append(error)
    diagram = Diagram(source=make_source(), pipe=pipe)
    states = []

    def on_progress(_pipe: Pipe) -> None:
        states.append(stage.status.state())
        if stage.status.state() == "ok":
            (pipe if closing == "pipeline" else diagram).close()

    stage.on_progress = on_progress

    try:
        task = diagram.refresh()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
        assert stage.runs == 1
        assert states == ["running", "ok"]
        assert pipe.status.state() == "cancelled"
        assert diagram.source.flow == (F.New,), "a cancelled run hands its flow back"
        assert errors == []
    finally:
        diagram.close()


class Parked(Pipe):
    """A stage that waits on a future nobody resolves."""

    gate: asyncio.Future | None = None

    async def run(self):
        self.gate = asyncio.get_running_loop().create_future()
        await self.gate
        self.outlet.value = self.inlet.value


@pytest.mark.asyncio
@pytest.mark.parametrize("closing", ["pipeline", "diagram"])
async def test_awaiting_refresh_raises_cancelled_when_closed_mid_run(
    closing: str,
) -> None:
    parked = Parked(observes=(F.New,), reports=(F.Layout,))
    pipe = Pipeline(pipes=[parked])
    errors = []
    pipe.on_error = lambda _pipe, error: errors.append(error)
    diagram = Diagram(source=make_source(), pipe=pipe)

    try:
        task = diagram.refresh()
        for _ in range(10):
            await asyncio.sleep(0)
        assert parked.gate is not None, "the run is parked inside the stage"
        (pipe if closing == "pipeline" else diagram).close()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=2)
        assert task.cancelled()
        assert pipe.status.state() == "cancelled"
        assert parked.status.state() == "cancelled"
        current = asyncio.current_task()
        if hasattr(current, "cancelling"):  # Python 3.11+
            assert current.cancelling() == 0, "only the run was cancelled"
        assert errors == []
        assert diagram.source.flow == (F.New,), "the taken flow is handed back"
    finally:
        diagram.close()


@pytest.mark.asyncio
async def test_closed_diagram_ignores_a_queued_successful_view_update() -> None:
    diagram = Diagram(source=make_source(), pipe=Pipe())
    displayed = make_source()
    diagram.view.source = displayed
    before = displayed.value
    diagram.pipe.outlet.value = make_source().value
    completed = asyncio.get_running_loop().create_future()
    completed.set_result(None)
    completed.add_done_callback(diagram._update_view)

    diagram.close()
    await asyncio.sleep(0)

    assert displayed.value is before


@pytest.mark.asyncio
async def test_stage_progress_closing_parent_keeps_cancelled_status() -> None:
    stage = Counting(observes=(F.New,), reports=(F.Layout,))
    pipe = Pipeline(pipes=[stage])
    stage.on_progress = lambda _stage: pipe.close()
    try:
        task = pipe.schedule_run()
        pipe.inlet.record(F.New)
        with pytest.raises(asyncio.CancelledError):
            await task
        assert pipe.status.state() == "cancelled"
        assert stage.status.state() == "cancelled"
        assert stage.runs == 0
    finally:
        pipe.close()


@pytest.mark.asyncio
async def test_closed_diagram_tool_refuses_trigger_before_scheduling() -> None:
    class Runnable(Tool):
        async def run(self):
            raise AssertionError("a closed diagram's tool must not run")

    tool = Runnable()
    diagram = Diagram(source=make_source(), pipe=Pipe())
    diagram.register_tool(tool)
    events = []
    tool.on_start(events.append)
    tool.on_done(events.append)
    diagram.close()
    msg = "^Runnable is closed and cannot run; build a new Runnable$"
    with pytest.raises(ClosedError, match=msg):
        tool.trigger()
    assert tool._task is None
    await asyncio.sleep(0)
    assert events == []


@pytest.mark.asyncio
async def test_stage_waiting_observer_closing_parent_keeps_cancelled_status() -> None:
    stage = Counting(observes=(F.New,), reports=(F.Layout,))
    pipe = Pipeline(pipes=[stage])
    stage.observe(lambda _change: pipe.close(), "status")
    try:
        pipe.inlet.record(F.New)
        task = pipe.schedule_run()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert pipe.status.state() == "cancelled"
        assert stage.status.state() == "cancelled"
        assert stage.runs == 0
        assert pipe.inlet.flow == (F.New,)
    finally:
        pipe.close()


def replace_defaults(diagram: Diagram) -> list[W.Widget]:
    """Replace the default ``layout`` and ``ui`` widgets; return the replacements."""
    tool = diagram.get_tool(ToggleCollapsedTool)
    given = []
    for widget in (diagram, diagram.view, diagram.toolbar):
        widget.layout = W.Layout()
        given.append(widget.layout)
    tool.ui = W.Button()
    given += [tool.ui, tool.ui.layout, tool.ui.style]
    return given


def build_replace_and_close() -> list[W.Widget]:
    source = make_source()
    diagram = Diagram(source=source)
    given = replace_defaults(diagram)
    diagram.close()
    close_widget(source)
    return given


def test_closing_closes_a_replaced_default_layout_and_ui() -> None:
    build_replace_and_close()
    before = live_widgets()
    given = [build_replace_and_close() for _ in range(ROUNDS)]

    assert live_widgets() - before == sum(map(len, given))
    assert all(is_open(widget) for widgets in given for widget in widgets)
