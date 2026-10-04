# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Replacing ``diagram.pipe`` closes and releases the old pipe (#180)."""

from __future__ import annotations

import asyncio
import contextlib
import functools
import gc
import weakref

import ipywidgets as W
import pytest
import traitlets as T
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
    elkjs,
    text_sizer,
)
from ipyelk.pipes.base import PipeStatus
from ipyelk.pipes.pipeline import Pipeline
from ipyelk.pipes.util import browser_roundtrip
from ipyelk.tools import PipelineProgressBar

ROUNDS = 10
#: seconds between ``run`` re-sends in the mid-run test
RESEND = 0.02

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
async def test_style_reaches_a_nested_pipeline_until_it_is_replaced() -> None:
    diagram = Diagram(source=make_source())
    inner = DefaultFlow()
    await replace(diagram, Pipeline(pipes=[inner]))
    diagram.style = {" .a": {"fill": "red"}}
    nested = sizer(inner)
    assert nested.style == {" .a": {"fill": "red"}}

    await replace(diagram, DefaultFlow())
    diagram.style = {" .b": {"fill": "blue"}}
    assert nested.style == {" .a": {"fill": "red"}}


@pytest.mark.asyncio
async def test_progress_bar_follows_the_new_pipe() -> None:
    diagram = Diagram(source=make_source())
    bar = diagram.get_tool(PipelineProgressBar)
    await refresh(diagram)
    old = diagram.pipe
    assert bar.pipe is old

    new = DefaultFlow()
    diagram.pipe = new
    assert bar.pipe is new
    assert old.on_progress is None
    await refresh(diagram)
    assert bar.pipe is new


def test_a_replaced_pipe_is_collected_without_a_refresh() -> None:
    diagram = Diagram(source=make_source())
    old = diagram.pipe
    old.status_update(PipeStatus.running())
    assert diagram.get_tool(PipelineProgressBar).pipe is old
    ref = weakref.ref(old)
    del old
    diagram.pipe = DefaultFlow()
    gc.collect()
    assert ref() is None


@pytest.mark.asyncio
async def test_swapping_back_to_a_replaced_pipe_is_refused_cleanly() -> None:
    diagram = Diagram(source=make_source())
    first, second = DefaultFlow(), DefaultFlow()
    await replace(diagram, first)
    await replace(diagram, second)

    with pytest.raises(T.TraitError, match="closed"):
        diagram.pipe = first

    assert diagram.pipe is second
    assert is_open(second)
    assert diagram.view.source is second.outlet
    assert all(tool.tee is second for tool in diagram.tools)
    await replace(diagram, DefaultFlow())


@pytest.mark.asyncio
async def test_replacing_the_pipe_mid_run_cancels_the_old_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IPYELK_NO_BROWSER")
    fast = functools.partial(browser_roundtrip, initial_delay=RESEND)
    monkeypatch.setattr(text_sizer, "browser_roundtrip", fast)
    monkeypatch.setattr(elkjs, "browser_roundtrip", fast)
    source = make_source()
    diagram = Diagram(source=source)
    old = diagram.pipe
    sent: list[Pipe] = []
    for sub in old.pipes:
        monkeypatch.setattr(sub, "send", lambda _msg, sub=sub: sent.append(sub))
    source.record("mine")
    task = diagram.refresh()
    assert task is not None
    sizer_ = sizer(old)
    for _ in range(50):
        if sent:
            break
        await asyncio.sleep(0)
    assert sent == [sizer_]
    assert "mine" not in source.flow

    new = DefaultFlow()
    diagram.pipe = new
    assert "mine" in source.flow
    sent.clear()
    await asyncio.sleep(3 * RESEND)
    assert task.cancelled()
    assert sent == []
    new.cancel()


@pytest.mark.asyncio
async def test_a_replaced_user_pipe_is_closed_but_not_what_it_was_given() -> None:
    """A diagram owns the pipe assigned to it: replacing it closes it, its
    sub-pipes and what they created, never the source or an outlet passed in.
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


def snapshot(diagram: Diagram) -> dict:
    pipe = diagram.pipe
    return {
        "pipe": pipe,
        "open": is_open(pipe),
        "owner": pipe._diagram() if pipe._diagram else None,
        "inlet": pipe.inlet,
        "outlet": pipe.outlet,
        "view.source": diagram.view.source,
        "links": list(diagram._pipe_links),
        "tees": [tool.tee for tool in diagram.tools],
        "bar": diagram.get_tool(PipelineProgressBar).pipe,
        "on_progress": pipe.on_progress,
    }


@pytest.mark.asyncio
async def test_a_pipe_another_diagram_owns_is_refused_without_side_effects() -> None:
    first = Diagram(source=make_source())
    await refresh(first)
    second = Diagram(source=make_source())
    await refresh(second)
    shared = first.pipe
    source = make_source()
    before = (snapshot(first), snapshot(second))
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match="another diagram"):
        second.pipe = shared
    with pytest.raises(T.TraitError, match="another diagram"):
        Diagram(source=source, pipe=shared)

    assert (snapshot(first), snapshot(second)) == before
    assert live_widgets() == widgets
    first.style = {" .a": {"fill": "red"}}
    assert sizer(shared).style == first.style
    assert sizer(second.pipe).style == {}


@pytest.mark.asyncio
async def test_refusing_a_nested_owned_pipe_has_no_side_effects() -> None:
    """The refusal changes nothing. Building a ``Pipeline`` around a live pipe
    already rewires that pipe's inlet (as on master), so the snapshot is taken
    after the wrappers are built.
    """
    first = Diagram(source=make_source())
    await refresh(first)
    second = Diagram(source=make_source())
    shared = first.pipe
    source = make_source()
    wrapped = Pipeline(pipes=[shared])
    deeper = Pipeline(pipes=[Pipeline(pipes=[shared])])
    before = (snapshot(first), snapshot(second))

    with pytest.raises(T.TraitError, match="another diagram"):
        second.pipe = wrapped
    with pytest.raises(T.TraitError, match="another diagram"):
        Diagram(source=source, pipe=deeper)

    assert (snapshot(first), snapshot(second)) == before
    assert is_open(shared)
    assert shared._diagram() is first


@pytest.mark.asyncio
async def test_wrapping_the_current_pipe_is_refused() -> None:
    diagram = Diagram(source=make_source())
    await refresh(diagram)
    current = diagram.pipe
    wrapper = Pipeline(pipes=[current])
    current.inlet = diagram.source
    before = snapshot(diagram)

    with pytest.raises(T.TraitError, match="wrap a new DefaultFlow"):
        diagram.pipe = wrapper

    assert snapshot(diagram) == before
    assert is_open(current)
    assert is_open(diagram.view.source)


def test_reassigning_a_diagrams_own_pipe_is_a_no_op() -> None:
    pipe = DefaultFlow()
    diagram = Diagram(source=make_source(), pipe=pipe)
    before = snapshot(diagram)
    diagram.pipe = pipe
    assert snapshot(diagram) == before
    assert before["owner"] is diagram


def test_only_the_top_level_pipe_is_owned() -> None:
    inner = DefaultFlow()
    diagram = Diagram(source=make_source(), pipe=Pipeline(pipes=[inner]))
    assert inner._diagram is None
    assert sizer(inner).style == diagram.style


def test_a_pipe_replaced_in_one_diagram_is_closed_for_another() -> None:
    first = Diagram(source=make_source())
    old = first.pipe
    first.pipe = DefaultFlow()
    with pytest.raises(T.TraitError, match="closed"):
        Diagram(source=make_source(), pipe=old)


def test_closing_a_diagram_releases_its_pipe() -> None:
    """A closed diagram leaves its pipe open for another diagram to take."""
    first = Diagram(source=make_source())
    pipe = first.pipe
    first.style = {" .a": {"fill": "red"}}
    first.close()

    second = Diagram(source=make_source(), pipe=pipe)

    assert is_open(pipe)
    assert pipe._diagram() is second
    assert second.view.source is pipe.outlet
    assert sizer(pipe).style == second.style == {}
    assert pipe.on_progress == second.get_tool(PipelineProgressBar).update
    first.style = {" .b": {"fill": "blue"}}
    assert sizer(pipe).style == {}


def test_a_collected_owner_releases_its_pipe() -> None:
    """Ownership is a weak reference; an open diagram is never collected (the
    widget registry holds it), so a stand-in plays the collected owner.
    """

    class Owner:
        comm = object()

    owner = Owner()
    pipe = DefaultFlow()
    pipe._diagram = weakref.ref(owner)
    with pytest.raises(T.TraitError, match="another diagram"):
        Diagram(source=make_source(), pipe=pipe)
    del owner
    gc.collect()

    diagram = Diagram(source=make_source(), pipe=pipe)
    assert pipe._diagram() is diagram
