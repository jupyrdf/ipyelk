# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A source and a view feed one open diagram (#178), and a diagram keeps its view
(#208).
"""

from __future__ import annotations

import asyncio
import gc
import re
import weakref

import pytest
import traitlets as T

from ipyelk import Diagram
from ipyelk.diagram import SprottyViewer
from ipyelk.exceptions import ClosedError
from ipyelk.pipes import MarkElementWidget, Pipe
from ipyelk.pipes import flows as F
from ipyelk.pipes.pipeline import Pipeline
from ipyelk.tools import ToggleCollapsedTool

from .test_diagram_close import Closer
from .test_pipe_replacement import is_open, live_widgets, make_source

pytestmark = pytest.mark.usefixtures("headless")

SHARED = re.escape(
    "MarkElementWidget feeds another open diagram; close that diagram with "
    "source.diagram.close() or give this one its own MarkElementWidget. To show one "
    "diagram in two places, display the same Diagram twice"
)
SHARED_VIEW = re.escape(
    "SprottyViewer belongs to another open diagram; give this one its own "
    "SprottyViewer. To show one diagram in two places, display the same Diagram twice"
)
FIXED_VIEW = re.escape(
    "Diagram.view cannot be replaced, because the tools are bound to it; close this "
    "Diagram, then build a new Diagram(source=..., view=...)"
)


@pytest.fixture
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


def snapshot(diagram: Diagram) -> dict:
    return {
        "source": diagram.source,
        "pipe": diagram.pipe,
        "inlet": diagram.pipe.inlet,
        "view": diagram.view,
        "view.source": diagram.view.source,
        "children": diagram.children,
        "tools": diagram.tools,
        "owner": diagram.source.diagram,
    }


def notifiers(widget: MarkElementWidget) -> int:
    return sum(
        len(h) for by_type in widget._trait_notifiers.values() for h in by_type.values()
    )


# a second diagram is refused ############################################################


@pytest.mark.parametrize("given", [True, False], ids=["given-source", "default-source"])
def test_a_source_of_an_open_diagram_is_refused_at_construction(given: bool) -> None:
    first = Diagram(source=make_source()) if given else Diagram()
    before = snapshot(first)
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match=SHARED):
        Diagram(source=first.source)

    assert live_widgets() == widgets
    assert snapshot(first) == before
    assert before["owner"] is first


def test_a_source_of_an_open_diagram_is_refused_on_assignment() -> None:
    first = Diagram(source=make_source())
    second = Diagram(source=make_source())
    before = [snapshot(first), snapshot(second)]
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match=SHARED):
        second.source = first.source

    assert live_widgets() == widgets
    assert [snapshot(first), snapshot(second)] == before


def test_the_diagram_of_a_source_is_read_only() -> None:
    diagram = Diagram(source=make_source())
    with pytest.raises(AttributeError):
        diagram.source.diagram = None  # type: ignore[misc]
    assert diagram.source.diagram is diagram


# running a notebook cell again ##########################################################


def test_running_the_diagram_cell_again_names_the_fix() -> None:
    source = make_source()  # cell 1
    diagram = Diagram(source=source)  # cell 2
    first = weakref.ref(diagram)
    with pytest.raises(T.TraitError, match=SHARED):
        diagram = Diagram(source=source)  # cell 2, run again
    del diagram
    gc.collect()
    assert source.diagram is first()  # ipywidgets keeps every open widget

    source.diagram.close()
    diagram = Diagram(source=source)
    assert source.diagram is diagram


def test_a_cell_that_closes_the_last_diagram_runs_again() -> None:
    source = make_source()
    runs = []
    for _ in range(3):  # the cell of the migration guide, run three times
        if source.diagram is not None:
            source.diagram.close()
        diagram = Diagram(source=source)
        runs.append(diagram)

    assert [run.closed for run in runs] == [True, True, False]
    assert source.diagram is diagram


def test_a_diagram_that_fails_to_build_releases_its_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Diagram, change: object = None) -> None:
        raise RuntimeError("boom")

    source = make_source()
    view, pipe = SprottyViewer(), Pipeline(pipes=[Pipe()])
    with monkeypatch.context() as patch:
        patch.setattr(Diagram, "_update_tools", boom)  # user code in a tool raises
        with pytest.raises(RuntimeError, match="boom"):
            Diagram(source=source, view=view, pipe=pipe)

    assert source.diagram is None
    assert not is_open(view)  # closed with the diagram
    assert not is_open(pipe)
    assert Diagram(source=source).pipe.inlet is source


def test_a_diagram_can_take_its_own_source_again() -> None:
    diagram = Diagram(source=make_source())
    diagram.source = diagram.source
    assert diagram.source.diagram is diagram


# a closed or replaced diagram releases its source #######################################


@pytest.mark.parametrize("assign", [False, True], ids=["construct", "assign"])
def test_a_closed_diagram_releases_its_source(assign: bool) -> None:
    first = Diagram(source=make_source())
    source = first.source
    first.close()
    assert source._diagram is None

    if assign:
        second = Diagram(source=make_source())
        second.source = source
    else:
        second = Diagram(source=source)

    assert second.pipe.inlet is source
    assert source.diagram is second
    assert is_open(source)


@pytest.mark.asyncio
async def test_a_diagram_closed_mid_run_releases_its_source() -> None:
    source = make_source()
    closer = Closer(observes=(F.New,))
    first = Diagram(source=source, pipe=Pipeline(pipes=[closer]))
    second: list[Diagram] = []
    closer.hook = lambda: (first.close(), second.append(Diagram(source=source)))

    task = first.refresh()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert second[0].pipe.inlet is source
    assert source.diagram is second[0]
    assert first.closed


def test_replacing_the_source_releases_the_old_one() -> None:
    first = Diagram(source=make_source())
    old, new = first.source, make_source()

    first.source = new
    second = Diagram(source=old)

    assert second.pipe.inlet is old
    assert first.pipe.inlet is new
    with pytest.raises(T.TraitError, match=SHARED):
        Diagram(source=new)


def test_a_new_source_is_refused_before_a_swap_when_a_stage_is_closed() -> None:
    stage = Pipeline(pipes=[Pipe()])
    diagram = Diagram(source=make_source(), pipe=Pipeline(pipes=[stage]))
    stage.close()
    before, new = snapshot(diagram), make_source()
    msg = "^Pipeline is closed; assign a new pipe before a new source$"

    with pytest.raises(T.TraitError, match=msg):
        diagram.source = new

    assert snapshot(diagram) == before
    assert new.diagram is None


def test_the_same_source_is_not_a_change_when_a_stage_is_closed() -> None:
    stage = Pipeline(pipes=[Pipe()])
    diagram = Diagram(source=make_source(), pipe=Pipeline(pipes=[stage]))
    stage.close()
    before = snapshot(diagram)

    diagram.source = diagram.source

    assert snapshot(diagram) == before


def test_closed_diagrams_are_collected_and_leave_no_notifiers() -> None:
    source = make_source()
    Diagram(source=source).close()
    gc.collect()
    count = notifiers(source)
    refs = []
    for _ in range(50):
        diagram = Diagram(source=source)
        refs.append(weakref.ref(diagram))
        diagram.close()
    del diagram
    gc.collect()

    assert notifiers(source) == count  # 0 added today: a guard for a future observer
    assert not any(ref() for ref in refs)
    assert source.diagram is None


# a diagram keeps its view ###############################################################


def test_a_view_given_at_construction_is_wired_and_bound() -> None:
    view = SprottyViewer()
    diagram = Diagram(source=make_source(), view=view)

    assert diagram.view is view
    assert view in diagram.children
    assert view.source is diagram.pipe.outlet
    assert list(diagram.tools[:4]) == [
        view.selection,
        view.painter,
        view.fit_tool,
        view.center_tool,
    ]
    assert diagram.get_tool(ToggleCollapsedTool).selection is view.selection


def test_a_new_view_is_refused_and_changes_nothing() -> None:
    diagram = Diagram(source=make_source())
    before = snapshot(diagram)
    other = SprottyViewer()

    with pytest.raises(T.TraitError, match=FIXED_VIEW) as raised:
        diagram.view = other

    assert not isinstance(raised.value, ClosedError)
    assert snapshot(diagram) == before
    assert other.source is None
    diagram.view = diagram.view  # the same view is not a change


@pytest.mark.parametrize("given", [True, False], ids=["given-view", "default-view"])
def test_a_view_of_an_open_diagram_is_refused(given: bool) -> None:
    first = Diagram(source=make_source(), view=SprottyViewer()) if given else Diagram()
    source = make_source()
    before = snapshot(first)
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match=SHARED_VIEW):
        Diagram(source=source, view=first.view)

    assert live_widgets() == widgets
    assert snapshot(first) == before
    assert source.diagram is None


def test_a_refused_construction_leaves_the_given_view_open() -> None:
    first = Diagram(source=make_source())
    view = SprottyViewer()
    with pytest.raises(T.TraitError, match=SHARED):
        Diagram(source=first.source, view=view)
    gc.collect()
    assert is_open(view)


def test_the_view_of_a_closed_diagram_is_refused_and_leaks_nothing() -> None:
    first = Diagram(source=make_source())
    first.close()
    widgets = live_widgets()
    msg = "^SprottyViewer is closed; give this diagram a new SprottyViewer$"

    with pytest.raises(T.TraitError, match=msg):
        Diagram(source=first.source, view=first.view)

    assert live_widgets() == widgets
    assert first.source.diagram is None
    assert Diagram(source=first.source).source.diagram is not None


def test_the_same_view_is_not_a_change_once_closed() -> None:
    diagram = Diagram(source=make_source())
    diagram.view.close()
    before = snapshot(diagram)

    diagram.view = diagram.view

    assert snapshot(diagram) == before


def test_a_closed_diagram_names_its_state_before_the_view_rule() -> None:
    diagram = Diagram()
    diagram.close()
    with pytest.raises(ClosedError, match="Diagram is closed and cannot set view"):
        diagram.view = SprottyViewer()


def test_a_pipe_replaced_after_construction_still_feeds_the_view() -> None:
    view = SprottyViewer()
    diagram = Diagram(source=make_source(), view=view)
    diagram.pipe = Pipeline(pipes=[Pipe()])
    assert view.source is diagram.pipe.outlet
