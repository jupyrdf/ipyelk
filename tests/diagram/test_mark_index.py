# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A pipe shares one kernel-only ``MarkIndex``, the source's (#237)."""

from __future__ import annotations

import ipywidgets as W
import pytest

from ipyelk import Diagram
from ipyelk.elements import Label, Node
from ipyelk.exceptions import DeprecatedAPIError
from ipyelk.pipes import MarkElementWidget, MarkIndex
from ipyelk.pipes import flows as F
from ipyelk.pipes.util import iter_pipes

from .test_no_inlet_swap import (  # ruff: ignore[unused-import]
    browser,
    settle,
    user_graph,
)
from .test_pipe_replacement import registry

#: the widgets one ``Diagram()`` opened on #235's head, before #237
WIDGETS_BEFORE_237 = 76


@pytest.fixture
def built(monkeypatch: pytest.MonkeyPatch) -> list[MarkIndex]:
    """Every ``MarkIndex`` constructed while the test runs."""
    found: list[MarkIndex] = []
    init = MarkIndex.__init__

    def spy(self, *args, **kwargs):
        found.append(self)
        init(self, *args, **kwargs)

    monkeypatch.setattr(MarkIndex, "__init__", spy)
    return found


def assert_shared(diagram: Diagram) -> None:
    index = diagram.source.index
    for pipe in iter_pipes(diagram.pipe):
        assert pipe.inlet.index is index, pipe
        assert pipe.outlet.index is index, pipe


def test_a_diagram_opens_no_index_and_no_layout_for_a_mark() -> None:
    assert not isinstance(MarkIndex(), W.Widget)
    before = set(registry())
    diagram = Diagram()
    opened = [widget for key, widget in registry().items() if key not in before]
    marks = [widget for widget in opened if isinstance(widget, MarkElementWidget)]

    assert marks, "the source and the stage outlets are still widgets"
    assert not any(isinstance(mark, W.DOMWidget) for mark in marks), "no layout"
    assert len(opened) <= WIDGETS_BEFORE_237 - 16, len(opened)
    diagram.close()
    diagram.source.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("browser")
async def test_every_stage_shares_the_one_index_of_the_source(built) -> None:
    diagram = Diagram(source=MarkElementWidget(value=user_graph()[0]))
    assert built == [], "no index is built before something reads one"
    await settle(diagram)

    assert len(built) == 1
    assert built[0] is diagram.source.index
    assert_shared(diagram)

    other = MarkElementWidget(value=Node(id="other"))
    diagram.source = other
    await settle(diagram)
    assert len(built) == 2
    assert built[1] is other.index
    assert_shared(diagram)
    diagram.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("browser")
async def test_dropping_the_source_elements_rebuilds_the_index_for_a_new_tree() -> None:
    """A collapse tool swaps the source tree, then drops the elements (#237)."""
    diagram = Diagram(source=MarkElementWidget(value=user_graph()[0]))
    await settle(diagram)
    source = diagram.source
    index = source.index
    assert "a" in index.elements

    leaf = Node(id="x", labels=[Label(id="lx", text="X")])
    source.value = Node(id="root2", children=[leaf])
    source.index.elements = None
    assert all(p.outlet.index.elements is None for p in iter_pipes(diagram.pipe))
    source.record(F.New)
    await diagram.refresh()

    assert diagram.pipe.status.exception is None
    assert source.index is index, "the index object stays, its elements are new"
    assert index.document["x"] is leaf
    assert index.document["lx"] is leaf.labels[0]
    assert "a" not in index.elements
    assert index.root is source.value
    assert_shared(diagram)
    assert diagram.view.source.value.children[0].id == "x"
    diagram.close()


def test_the_widget_names_of_an_index_and_a_mark_raise_their_removed_error() -> None:
    mark = MarkElementWidget()
    for owner, name in [(mark.index, "comm"), (mark.index, "close"), (mark, "layout")]:
        with pytest.raises(DeprecatedAPIError, match=r"ipyelk 3\.0"):
            getattr(owner, name)
    assert mark.get_state()["_model_name"] == "WidgetModel"
    assert mark.get_state()["_model_module"] == "@jupyter-widgets/base"
    mark.close()
