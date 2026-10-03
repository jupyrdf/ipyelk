# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Replacing ``diagram.pipe`` closes and releases the old pipe (#180)."""

from __future__ import annotations

import asyncio
import contextlib
import gc
import weakref

import ipywidgets as W
import pytest
from ipywidgets.widgets import widget as widget_module

from ipyelk import Diagram
from ipyelk.diagram.flow import DefaultFlow
from ipyelk.elements import Node
from ipyelk.pipes import (
    BrowserTextSizer,
    ElkJS,
    MarkElementWidget,
    Pipe,
    ValidationPipe,
    VisibilityPipe,
)
from ipyelk.tools import PipelineProgressBar

ROUNDS = 10

pytestmark = pytest.mark.usefixtures("headless")


@pytest.fixture
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


def registry() -> dict:
    instances = getattr(widget_module, "_instances", None)
    return W.Widget._active_widgets if instances is None else instances


def live_widgets() -> int:
    gc.collect()
    return len(registry())


def is_open(widget: W.Widget) -> bool:
    return widget.comm is not None


def make_source() -> MarkElementWidget:
    root = Node(id="root")
    root.add_child(Node(id="a"))
    return MarkElementWidget(value=root)


async def refresh(diagram: Diagram) -> None:
    with contextlib.suppress(asyncio.TimeoutError):
        await diagram.refresh()
    await asyncio.sleep(0)


async def replace(diagram: Diagram, pipe: Pipe, show_view: bool = False) -> None:
    diagram.pipe = pipe
    if show_view:
        assert pipe.status_widget is not None
    await refresh(diagram)


def sizer(pipe: Pipe) -> BrowserTextSizer:
    return next(p for p in pipe.pipes if isinstance(p, BrowserTextSizer))


@pytest.mark.asyncio
@pytest.mark.parametrize("show_view", [False, True], ids=["view-hidden", "view-shown"])
async def test_replacing_the_pipe_adds_no_live_widgets(show_view: bool) -> None:
    diagram = Diagram(source=make_source())
    if show_view:
        assert diagram.pipe.status_widget is not None
    await refresh(diagram)
    await replace(diagram, DefaultFlow(), show_view)
    before = live_widgets()
    for _ in range(ROUNDS):
        await replace(diagram, DefaultFlow(), show_view)
    assert live_widgets() - before == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("show_view", [False, True], ids=["view-hidden", "view-shown"])
async def test_replaced_pipes_are_collected(show_view: bool) -> None:
    diagram = Diagram(source=make_source())
    if show_view:
        assert diagram.pipe.status_widget is not None
    await refresh(diagram)
    built = weakref.ref(diagram.pipe)
    await replace(diagram, DefaultFlow(), show_view)
    assigned = weakref.ref(diagram.pipe)
    await replace(diagram, DefaultFlow(), show_view)
    gc.collect()
    assert built() is None
    assert assigned() is None


@pytest.mark.asyncio
async def test_shared_widgets_survive_and_the_new_pipe_renders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = make_source()
    diagram = Diagram(source=source)
    view = diagram.view
    await refresh(diagram)
    for _ in range(3):
        await replace(diagram, DefaultFlow())

    pipe = DefaultFlow()
    valid = next(p for p in pipe.pipes if isinstance(p, ValidationPipe))
    runs = []
    real_run = valid.run

    async def run():
        runs.append(True)
        await real_run()

    monkeypatch.setattr(valid, "run", run)
    await replace(diagram, pipe)

    assert diagram.source is source
    assert diagram.view is view
    assert pipe.inlet is source
    for widget in (source, view, pipe, pipe.inlet, pipe.outlet):
        assert is_open(widget)
    assert view.source is pipe.outlet
    assert runs
    assert pipe.outlet.value is not None
    assert all(tool.tee is pipe for tool in diagram.tools)


@pytest.mark.asyncio
async def test_style_follows_the_new_pipe_only() -> None:
    diagram = Diagram(source=make_source())
    old = sizer(diagram.pipe)
    diagram.style = {" .a": {"fill": "red"}}
    assert old.style == diagram.style
    old_style = dict(old.style)

    new = DefaultFlow()
    await replace(diagram, new)
    assert sizer(new).style == diagram.style

    diagram.style = {" .b": {"fill": "blue"}}
    assert sizer(new).style == {" .b": {"fill": "blue"}}
    assert old.style == old_style


@pytest.mark.asyncio
async def test_progress_bar_follows_the_new_pipe() -> None:
    diagram = Diagram(source=make_source())
    bar = diagram.get_tool(PipelineProgressBar)
    await refresh(diagram)
    old = diagram.pipe
    assert bar.pipe is old

    new = DefaultFlow()
    await replace(diagram, new)
    assert bar.pipe is new
    assert old.on_progress is None


@pytest.mark.asyncio
async def test_a_replaced_user_pipe_is_closed_but_not_what_it_was_given() -> None:
    """A diagram owns the pipe assigned to it: replacing it closes it, and every
    widget it created, but never the source or a widget passed in to it.
    """
    source = make_source()
    diagram = Diagram(source=source)
    given = MarkElementWidget()
    mine = DefaultFlow(
        pipes=[
            ValidationPipe(),
            BrowserTextSizer(),
            VisibilityPipe(),
            ElkJS(outlet=given),
        ]
    )
    await replace(diagram, mine)
    assert diagram.view.source is given
    created = [mine, *mine.pipes, *(p.outlet for p in mine.pipes[:-1])]

    await replace(diagram, DefaultFlow())

    assert not any(is_open(widget) for widget in created)
    assert is_open(given)
    assert is_open(source)
    assert diagram.view.source is diagram.pipe.outlet


@pytest.mark.asyncio
async def test_replacing_one_diagrams_pipe_leaves_a_sharing_diagram_alone() -> None:
    source = make_source()
    first = Diagram(source=source)
    second = Diagram(source=source)
    await refresh(second)

    await replace(first, DefaultFlow())
    second.source.record("new")
    await refresh(second)

    assert is_open(source)
    assert is_open(second.pipe)
    assert second.view.source is second.pipe.outlet
    assert second.pipe.outlet.value is not None


def test_closing_a_pipe_closes_what_it_created_not_its_inlet() -> None:
    source = make_source()
    pipe = DefaultFlow(inlet=source)
    assert pipe.status_widget is not None
    subs = list(pipe.pipes)
    marks = [p.outlet for p in subs]

    pipe.close()

    assert is_open(source)
    assert is_open(source.index)
    assert not any(is_open(widget) for widget in [pipe, *subs, *marks])
    assert not is_open(pipe.status_widget)
