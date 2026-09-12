# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Tool.disabled`` is an execution guard and disables the supported controls."""

import asyncio
import warnings

import pytest

from ipyelk.exceptions import DeprecatedAPIError
from ipyelk.tools import (
    PipelineProgressBar,
    SetTool,
    ToggleCollapsedTool,
    Tool,
    ToolButton,
)


class _Runs(Tool):
    async def run(self):
        pass


@pytest.mark.asyncio
async def test_disabled_rejects_trigger_before_anything_is_scheduled():
    tool = _Runs(disabled=True)
    starts, dones = [], []
    tool.on_start(starts.append)
    tool.on_done(dones.append)
    with pytest.raises(RuntimeError, match="disabled"):
        tool.trigger()
    await asyncio.sleep(0)
    assert tool._task is None
    assert (starts, dones) == ([], [])
    tool.disabled = False
    await tool.trigger()
    await asyncio.sleep(0)
    assert dones == [tool]


def test_disabled_button_click_is_rejected_and_control_follows_the_tool(caplog):
    seen = []
    tool = ToolButton(on_click=seen.append, disabled=True)
    assert tool.ui.disabled is True  # lazily built ui picks up the state
    with pytest.raises(RuntimeError, match="disabled"):
        tool.check_enabled()
    # a programmatic click (the browser cannot click a disabled button at all):
    # ipywidgets' CallbackDispatcher reports the rejection instead of raising
    tool.ui.click()
    assert seen == []
    assert "ToolButton is disabled" in caplog.text
    tool.disabled = False
    assert tool.ui.disabled is False
    tool.ui.click()
    assert seen == [tool]


def test_only_controls_with_a_disabled_trait_are_touched():
    set_tool = SetTool()
    set_tool.disabled = True
    assert not set_tool.ui.has_trait("disabled")  # an HBox is walked through...
    assert [b.disabled for b in set_tool.ui.children] == [
        True,
        True,
        True,
    ]  # ...to these
    collapser = ToggleCollapsedTool()
    collapser.disabled = True
    assert collapser.ui.disabled is True
    bar = PipelineProgressBar()
    bar.disabled = True  # a progress bar has no disabled trait: nothing to do, no error
    assert not bar.ui.has_trait("disabled")


def test_disable_is_a_hard_error_throughout_3x():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(DeprecatedAPIError, match=r"tool\.disabled") as info:
            Tool().disable = True
        assert "3.0" in str(info.value)
        with pytest.raises(DeprecatedAPIError, match=r"tool\.disabled"):
            Tool(disable=True)
        with pytest.raises(DeprecatedAPIError, match=r"tool\.disabled"):
            _ = Tool().disable
