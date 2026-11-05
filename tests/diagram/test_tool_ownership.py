# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""An open diagram's tools and toolbar cannot be stolen (#249)."""

import gc

import pytest
import traitlets as T

from ipyelk import Diagram
from ipyelk.diagram import SprottyViewer
from ipyelk.tools import PipelineProgressBar, Selection, ToggleCollapsedTool, Toolbar

pytestmark = pytest.mark.usefixtures("headless")


@pytest.fixture
def headless(monkeypatch):
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


def snapshot(diagram):
    return (
        diagram.tools,
        diagram.toolbar,
        diagram.children,
        diagram.pipe.on_progress,
        tuple(
            (t.tee, tuple(t._on_done_handlers.callbacks), t.closed)
            for t in diagram.tools
        ),
    )


@pytest.mark.parametrize("kind", ["tools", "toolbar"])
@pytest.mark.parametrize("operation", ["construct", "assign"])
def test_foreign_widgets_are_refused_without_mutation_or_close(kind, operation):
    first, second = Diagram(), Diagram()
    before = snapshot(first), snapshot(second)
    value = getattr(first, kind)
    action = (
        (lambda: Diagram(**{kind: value}))
        if operation == "construct"
        else (lambda: setattr(second, kind, value))
    )
    with pytest.raises(
        T.TraitError,
        match=r"belongs to another open diagram.*own.*display the same Diagram twice",
    ):
        action()
    gc.collect()  # failed constructors must not close their borrowed widgets
    assert (snapshot(first), snapshot(second)) == before
    assert first.toolbar.comm is not None


@pytest.mark.parametrize("kind", ["toggle", "progress"])
def test_register_checks_before_changing_dependencies_or_callbacks(kind):
    first, second = Diagram(), Diagram()
    cls = ToggleCollapsedTool if kind == "toggle" else PipelineProgressBar
    tool = first.get_tool(cls)
    before = snapshot(first), snapshot(second), tool.trait_values()
    with pytest.raises(T.TraitError, match="belongs to another open diagram"):
        second.register_tool(tool)
    assert (snapshot(first), snapshot(second), tool.trait_values()) == before


def test_tuple_is_checked_before_releasing_any_existing_tool():
    first, second = Diagram(), Diagram()
    before = snapshot(first), snapshot(second)
    with pytest.raises(T.TraitError, match="belongs to another open diagram"):
        second.tools = (*second.tools, first.get_tool(ToggleCollapsedTool))
    assert (snapshot(first), snapshot(second)) == before


def test_removed_tool_rebinds_and_survives_original_close():
    first, second = Diagram(), Diagram()
    tool = first.get_tool(ToggleCollapsedTool)
    first.tools = tuple(t for t in first.tools if t is not tool)
    second.register_tool(tool)
    first.close()
    assert not tool.closed
    assert tool.selection is second.view.selection
    assert tool.tee is second.pipe
    assert tool._on_done_handlers.callbacks.count(second.refresh) == 1
    assert first.refresh not in tool._on_done_handlers.callbacks
    second.tools = second.tools
    second.register_tool(tool)
    assert tool._on_done_handlers.callbacks.count(second.refresh) == 1
    second.close()
    assert tool.closed


@pytest.mark.parametrize(
    "name", ["selection", "painter", "hover", "viewport", "fit_tool", "center_tool"]
)
def test_view_tools_stay_with_their_view_even_when_not_registered(name):
    first, second = Diagram(), Diagram()
    tool = getattr(first.view, name)
    first.tools = tuple(t for t in first.tools if t is not tool)
    with pytest.raises(T.TraitError, match="belongs to another open diagram"):
        second.register_tool(tool)
    assert not tool.closed
    second.close()
    assert not tool.closed
    first.close()
    assert tool.closed


def test_toolbar_can_be_released_by_replacement():
    first, second = Diagram(), Diagram()
    toolbar = first.toolbar
    first.toolbar = Toolbar()
    second.toolbar = toolbar
    before = second.tools
    first.tools = ()
    assert second.tools == before  # the former owner's default link was removed
    first.close()
    assert toolbar.comm is not None
    second.close()
    assert toolbar.comm is None


@pytest.mark.parametrize(
    "name", ["selection", "hover", "viewport", "painter", "fit_tool", "center_tool"]
)
def test_another_viewer_cannot_hide_a_tools_owner(name):
    first = Diagram()
    tool = getattr(first.view, name)
    with pytest.raises(T.TraitError, match="belongs to another open viewer or diagram"):
        SprottyViewer(**{name: tool})
    assert tool._viewer() is first.view
    assert not tool.closed


def test_replacing_a_view_tool_releases_its_claim():
    first, second = Diagram(), Diagram()
    tool = first.view.selection
    first.tools = tuple(t for t in first.tools if t is not tool)
    first.view.selection = Selection()
    second.register_tool(tool)
    first.close()
    assert not tool.closed
    second.close()
    assert tool.closed
