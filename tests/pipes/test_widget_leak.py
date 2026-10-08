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
from ipyelk.elements import Compartment, Node, Record
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes.base import PipeStatus, rep_elapsed
from ipyelk.pipes.pipeline import Pipeline, PipelineStatusView

REFRESHES = 10


def registry() -> dict:
    """The live-widget registry: ``_instances`` on 8.1+, ``_active_widgets`` on 8.0."""
    instances = getattr(widget_module, "_instances", None)
    return W.Widget._active_widgets if instances is None else instances


def live_widgets() -> int:
    gc.collect()
    return len(registry())


def is_closed(widget: W.Widget) -> bool:
    return widget.comm is None


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


def test_record_dump_adds_no_live_widgets() -> None:
    """``Record`` sets its children's size options as strings, not widgets."""
    record = Record(children=[Compartment(), Compartment()])
    before = live_widgets()
    record.model_dump()
    record.model_dump_json()
    assert live_widgets() == before
    assert record.children[0].layoutOptions["org.eclipse.elk.nodeSize.minimum"] == (
        "(80, 20)"
    )


def test_pipe_status_is_not_a_widget() -> None:
    assert not issubclass(PipeStatus, W.Widget)


@pytest.mark.asyncio
@pytest.mark.usefixtures("headless")
async def test_status_rows_are_reused_and_current() -> None:
    diagram = make_diagram()
    pipe = diagram.pipe
    view = pipe.status_widget
    assert isinstance(view, PipelineStatusView)
    view.update_children(pipe)
    rows = list(view._rows)
    before = live_widgets()
    for _ in range(100):
        view.update_children(pipe)
    assert live_widgets() == before
    assert len(view._rows) == len(pipe.pipes)
    assert all(new is old for new, old in zip(view._rows, rows, strict=True))

    await refresh(diagram)
    for row, sub in zip(view._rows, pipe.pipes, strict=True):
        html = row.children[1].html.value
        assert f"elk-pipe-disposition-{sub.status.disposition.value}" in html
        assert f'class="elk-pipe-status">{sub.status.state()}<' in html
        assert f'class="elk-pipe-elapsed">{rep_elapsed(sub.status.elapsed)}<' in html


def test_status_rows_are_rebuilt_when_pipes_change() -> None:
    pipe = make_diagram().pipe
    view = pipe.status_widget
    view.update_children(pipe)
    old_rows = list(view._rows)
    sub_views = [p.status_widget for p in pipe.pipes]

    pipe.pipes = pipe.pipes[:-1]
    view.update_children(pipe)

    assert len(view._rows) == len(pipe.pipes)
    for row in old_rows:
        space, _, accessor = row.children
        for widget in (row, space, accessor):
            assert is_closed(widget)
            assert is_closed(widget.layout)
        assert is_closed(space.style)
        assert is_closed(accessor.style)
    assert not any(is_closed(sub_view) for sub_view in sub_views)


def test_collapse_toggle_adds_no_live_widgets() -> None:
    view = make_diagram().pipe.status_widget
    view.collapsed = False
    before = live_widgets()
    for _ in range(50):
        view.collapsed = not view.collapsed
    assert live_widgets() == before


def test_empty_pipeline_shows_its_header() -> None:
    view = Pipeline().status_widget
    assert view.children == (view.header,)
    assert view.header.children == (view.toggle_btn, view.html)


def test_replaced_views_are_shown() -> None:
    pipe = make_diagram().pipe
    view = pipe.status_widget
    custom = W.HTML("custom")
    pipe.pipes[0].status_widget = custom
    html = W.HTML("summary")
    view.html = html
    view.update_children(pipe)
    assert view._rows[0].children[1] is custom
    assert view.header.children[1] is html


def test_new_status_notifies_observers() -> None:
    diagram = make_diagram()
    sub = diagram.pipe.pipes[0]
    seen = []
    sub.observe(lambda change: seen.append(change["new"]), "status")
    sub.status = PipeStatus.finished()
    sub.status = PipeStatus.finished()
    assert len(seen) == 2
