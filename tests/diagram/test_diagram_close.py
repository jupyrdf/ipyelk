# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Diagram.close()`` closes what the diagram owns (#191)."""

from __future__ import annotations

import gc
import weakref

import pytest

from ipyelk import Diagram
from ipyelk.diagram.flow import DefaultFlow
from ipyelk.pipes import (
    BrowserTextSizer,
    ElkJS,
    MarkElementWidget,
    ValidationPipe,
    VisibilityPipe,
)
from ipyelk.pipes.pipeline import Pipeline
from ipyelk.tools import SetTool
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
