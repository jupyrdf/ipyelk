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
from ipyelk.tools import ControlOverlay, SetTool, Tool, Toolbar
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
    close_widget(source.index)


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

    assert not is_open(diagram)
    for widget in [*subs, *created, view, toolbar, *tools, *uis]:
        assert not is_open(widget), widget
    for widget in (source, source.index, given, given.index):
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
    with pytest.raises(T.TraitError, match=msg):
        ENTRY_POINTS[action](diagram)

    assert {name: getattr(diagram, name) for name in TRAITS} == before


@pytest.mark.parametrize("owned", [True, False], ids=["diagram-pipe", "standalone"])
def test_a_closed_pipeline_refuses_pipes_and_keeps_them(owned: bool) -> None:
    diagram = Diagram(source=make_source()) if owned else None
    pipe = diagram.pipe if diagram else Pipeline(pipes=[ValidationPipe()])
    stages = list(pipe.pipes)
    (diagram or pipe).close()
    name = type(pipe).__name__
    msg = f"^{name} is closed and cannot set pipes; use a new pipe$"

    for pipes in ([ValidationPipe(), ValidationPipe()], [stages[0]], []):
        with pytest.raises(T.TraitError, match=msg):
            pipe.pipes = pipes
        assert pipe.pipes == stages


@pytest.mark.asyncio
async def test_a_closed_pipeline_refuses_runs() -> None:
    diagram = Diagram(source=make_source())
    pipe = diagram.pipe
    pipe.close()
    msg = "^DefaultFlow is closed and cannot run; use a new pipe$"

    with pytest.raises(T.TraitError, match=msg):
        diagram.refresh()
    with pytest.raises(T.TraitError, match=msg):
        pipe.schedule_run()
    with pytest.raises(T.TraitError, match=msg):
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
    assert not is_open(diagram)


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
