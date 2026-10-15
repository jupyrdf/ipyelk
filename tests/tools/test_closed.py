# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A closed tool refuses to run (#218); an open tool runs whatever its old diagram."""

from __future__ import annotations

import asyncio

import pytest

from ipyelk.diagram import Diagram
from ipyelk.elements import Node
from ipyelk.exceptions import ClosedError
from ipyelk.pipes import MarkElementWidget, Pipe
from ipyelk.tools import ToggleCollapsedTool, Tool


def _collapsible() -> tuple[MarkElementWidget, Node]:
    """A source whose node ``a`` has one child, ``c``, to collapse."""
    root, a, c = Node(id="root"), Node(id="a"), Node(id="c")
    a.add_child(c)
    root.add_child(a)
    return MarkElementWidget(value=root), c


def _closed_message(cls: type) -> str:
    name = cls.__name__
    return f"^{name} is closed and cannot run; build a new {name}$"


@pytest.mark.asyncio
async def test_tool_of_a_closed_diagram_refuses_to_run():
    source, child = _collapsible()
    diagram = Diagram(source=source, pipe=Pipe())
    tool = diagram.get_tool(ToggleCollapsedTool)
    diagram.view.selection.ids = ("a",)
    button = tool.ui
    assert not tool.closed
    flow = source.flow

    diagram.close()

    assert tool.closed
    assert source.comm is not None, "the source stays open"
    msg = _closed_message(ToggleCollapsedTool)
    with pytest.raises(ClosedError, match=msg):
        tool.trigger()
    with pytest.raises(ClosedError, match=msg):
        tool.check_enabled()
    assert tool._task is None
    button.click()  # ipywidgets catches the button callback's exception
    await asyncio.sleep(0)
    assert not child.properties.hidden, "a closed tool must not edit the source"
    assert source.flow == flow, "nor record its reports"


def test_closed_is_false_before_and_true_after_close_and_double_close_is_silent():
    class Runnable(Tool):
        async def run(self):
            pass

    tool = Runnable()
    assert tool.closed is False
    tool.close()
    assert tool.closed is True
    tool.close()  # closing again does nothing
    assert tool.closed is True
    with pytest.raises(ClosedError, match=_closed_message(Runnable)):
        tool.trigger()
    with pytest.raises(AttributeError):
        tool.closed = False  # read-only, like Diagram.closed and Pipe.closed


@pytest.mark.asyncio
async def test_tool_moved_to_an_open_diagram_still_runs_after_the_old_one_closes():
    """The rule is the tool's own state: a closed *former* diagram does not refuse it.

    ``Diagram.close()`` closes the tools still in its ``tools``, so a tool moves
    to another diagram by leaving the first one's ``tools`` before that closes.
    """
    old_source, old_child = _collapsible()
    old = Diagram(source=old_source, pipe=Pipe())
    tool = old.get_tool(ToggleCollapsedTool)
    old.tools = tuple(t for t in old.tools if t is not tool)

    source, child = _collapsible()
    diagram = Diagram(source=source, pipe=Pipe())
    diagram.register_tool(tool)
    old.close()
    assert old.closed
    assert not tool.closed

    diagram.view.selection.ids = ("a",)
    await tool.trigger()
    assert child.properties.hidden is True
    assert not old_child.properties.hidden
    diagram.close()
