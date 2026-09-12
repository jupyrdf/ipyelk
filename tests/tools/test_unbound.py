# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Tools construct unbound (explicit ``None`` dependencies) and bind later."""

import pytest

from ipyelk.diagram import Diagram
from ipyelk.pipes import Pipe
from ipyelk.tools import PipelineProgressBar, Selection, SetTool, ToggleCollapsedTool


def test_unbound_tools_construct_with_none_dependencies():
    assert PipelineProgressBar().pipe is None
    assert ToggleCollapsedTool().selection is None
    assert SetTool().selection is None


def test_unbound_collapser_has_a_disabled_button_and_rejects_trigger():
    tool = ToggleCollapsedTool()
    assert tool.missing_dependencies() == ("selection",)
    assert tool.ui.disabled is True
    with pytest.raises(RuntimeError, match="not bound: selection is None"):
        tool.trigger()
    assert tool._task is None

    tool.selection = Selection()  # construct-then-bind
    assert tool.missing_dependencies() == ()
    assert tool.ui.disabled is False
    tool.selection = None
    assert tool.ui.disabled is True


def test_unbound_set_tool_disables_its_buttons_until_bound():
    tool = SetTool()
    assert [b.disabled for b in tool.ui.children] == [True] * 3
    tool.selection = Selection()
    assert [b.disabled for b in tool.ui.children] == [False] * 3


def test_disabled_and_unbound_compose():
    tool = ToggleCollapsedTool(selection=Selection(), disabled=True)
    assert tool.ui.disabled is True
    tool.disabled = False
    assert tool.ui.disabled is False


def test_progress_bar_binds_on_first_update():
    bar = PipelineProgressBar()
    assert bar.missing_dependencies() == ("pipe",)
    pipe = Pipe()
    bar.update(pipe)
    assert bar.pipe is pipe
    assert bar.missing_dependencies() == ()


def test_register_tool_binds_the_selection():
    diagram = Diagram()
    tool = ToggleCollapsedTool()
    diagram.register_tool(tool)
    assert tool.selection is diagram.view.selection
    assert tool.ui.disabled is False
    # the progress bar binds on the first progress event, not at construction
    bar = diagram.get_tool(PipelineProgressBar)
    assert bar.pipe is None
    bar.update(diagram.pipe)
    assert bar.pipe is diagram.pipe
