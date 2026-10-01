# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Refreshing a diagram must not leave live widgets behind (#176)."""

from __future__ import annotations

import asyncio
import contextlib
import gc

import ipywidgets as W
import pytest
from ipywidgets.widgets import widget as widget_module

from ipyelk import Diagram
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.base import PipeStatus, rep_elapsed
from ipyelk.pipes.pipeline import PipelineStatusView

REFRESHES = 10


def registry() -> dict:
    """The live-widget registry (``Widget.widgets`` is deprecated in 8.1)."""
    instances = getattr(widget_module, "_instances", None)
    return W.Widget.widgets if instances is None else instances


def live_widgets() -> int:
    gc.collect()
    return len(registry())


def live_status_widgets() -> int:
    gc.collect()
    return sum(isinstance(w, PipeStatus) for w in list(registry().values()))


def make_diagram() -> Diagram:
    root = Node(id="root")
    root.add_child(Node(id="a"))
    return Diagram(source=MarkElementWidget(value=root))


async def refresh(diagram: Diagram) -> None:
    with contextlib.suppress(asyncio.TimeoutError):  # headless: no browser answers
        await diagram.refresh()
    await asyncio.sleep(0)


@pytest.fixture
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


@pytest.mark.asyncio
@pytest.mark.usefixtures("headless")
@pytest.mark.parametrize("show_view", [False, True], ids=["view-hidden", "view-shown"])
async def test_refresh_adds_no_live_widgets(show_view: bool) -> None:
    diagram = make_diagram()
    if show_view:
        assert diagram.pipe.status_widget is not None
    await refresh(diagram)
    before = live_widgets()
    for _ in range(REFRESHES):
        await refresh(diagram)
    assert live_widgets() - before == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("headless")
async def test_pipe_statuses_are_bounded() -> None:
    diagram = make_diagram()
    assert diagram.pipe.status_widget is not None
    await refresh(diagram)
    first = live_status_widgets()
    for _ in range(REFRESHES):
        await refresh(diagram)
    after = live_status_widgets()
    assert after <= len(diagram.pipe.pipes) + 1
    assert after <= first


@pytest.mark.asyncio
@pytest.mark.usefixtures("headless")
async def test_status_rows_are_reused_and_current() -> None:
    diagram = make_diagram()
    pipe = diagram.pipe
    view = pipe.status_widget
    assert isinstance(view, PipelineStatusView)
    view.update_children(pipe)
    before = live_widgets()
    for _ in range(100):
        view.update_children(pipe)
    assert live_widgets() == before
    assert len(view.statuses) == len(pipe.pipes)

    await refresh(diagram)
    for row, sub in zip(view.statuses, pipe.pipes):
        html = row.children[1].html.value
        assert f"elk-pipe-disposition-{sub.status.disposition.value}" in html
        assert f'class="elk-pipe-status">{sub.status.state()}<' in html
        assert f'class="elk-pipe-elapsed">{rep_elapsed(sub.status.elapsed)}<' in html


def test_status_rows_are_rebuilt_when_pipes_change() -> None:
    pipe = make_diagram().pipe
    view = pipe.status_widget
    view.update_children(pipe)
    old_rows = list(view.statuses)
    sub_views = [p.status_widget for p in pipe.pipes]

    pipe.pipes = pipe.pipes[:-1]
    view.update_children(pipe)

    assert len(view.statuses) == len(pipe.pipes)
    assert all(row.comm is None for row in old_rows)
    assert all(sub_view.comm is not None for sub_view in sub_views)


def test_new_status_notifies_observers() -> None:
    diagram = make_diagram()
    sub = diagram.pipe.pipes[0]
    seen = []
    sub.observe(lambda change: seen.append(change["new"]), "status")
    sub.status = PipeStatus.finished()
    sub.status = PipeStatus.finished()
    assert len(seen) == 2
