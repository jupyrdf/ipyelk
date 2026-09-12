# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Tool`` execution lifecycle: trigger/run, on_start, success-only on_done."""

from __future__ import annotations

import asyncio
import warnings

import pytest
import traitlets as T

from ipyelk.exceptions import DeprecatedAPIError, RemovedAPI
from ipyelk.pipes import Pipe
from ipyelk.tools import SetTool, Tool, ToolButton
from ipyelk.tools.toolbar import Toolbar


class _Recording(Tool):
    """Runs to a checkpoint, then does what ``outcome`` says."""

    def __init__(self, outcome: str = "ok", **kwargs):
        super().__init__(**kwargs)
        self.outcome = outcome
        self.events: list[str] = []
        self.gate = asyncio.Event()
        self.on_start(lambda tool: self.events.append(f"start:{tool is self}"))
        self.on_done(lambda tool: self.events.append(f"done:{tool is self}"))

    async def run(self):
        self.events.append("run")
        await self.gate.wait()
        if self.outcome == "error":
            raise ValueError("boom")


def _wired(outcome: str = "ok") -> tuple[_Recording, Pipe]:
    pipe = Pipe()
    pipe.inlet.flow = ("pending",)
    return _Recording(outcome, tee=pipe, reports=("r",)), pipe


@pytest.mark.asyncio
async def test_success_fires_start_then_done_with_reports_recorded():
    tool, pipe = _wired()
    task = tool.trigger()
    assert tool.events == []  # on_start fires when the work starts, not at trigger
    await asyncio.sleep(0)
    assert tool.events == ["start:True", "run"]
    assert pipe.inlet.flow == ("pending",)  # nothing recorded before the work ends

    seen_at_done = []
    tool.on_done(lambda _tool: seen_at_done.append(pipe.inlet.flow))
    tool.gate.set()
    await task
    await asyncio.sleep(0)
    assert seen_at_done == [("pending", "r")]  # recorded before on_done
    assert tool.events[-1] == "done:True"  # several on_done listeners coexist
    assert tool._task is None


@pytest.mark.asyncio
async def test_failure_records_reports_logs_and_never_fires_done(caplog):
    tool, pipe = _wired("error")
    task = tool.trigger()
    await asyncio.sleep(0)
    tool.gate.set()
    with pytest.raises(ValueError, match="boom"):
        await task
    await asyncio.sleep(0)
    assert tool.events == ["start:True", "run"]
    assert pipe.inlet.flow == ("pending", "r")  # partial changes stay pending
    assert "Error running tool" in caplog.text


@pytest.mark.asyncio
async def test_cancellation_records_reports_and_never_fires_done():
    tool, pipe = _wired()
    task = tool.trigger()
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert tool.events == ["start:True", "run"]
    assert pipe.inlet.flow == ("pending", "r")


@pytest.mark.asyncio
async def test_retrigger_supersedes_stale_task_without_clobbering_new_state():
    tool, pipe = _wired()
    first = tool.trigger()
    await asyncio.sleep(0)
    second = tool.trigger()  # cancels ``first``
    assert tool._task is second
    await asyncio.sleep(0)  # first's cancellation + done callback run here
    assert first.cancelled()
    assert tool._task is second  # stale completion left the new task in place
    assert tool.events == ["start:True", "run", "start:True", "run"]
    assert "done:True" not in tool.events

    tool.gate.set()
    await second
    await asyncio.sleep(0)
    assert tool.events[-1] == "done:True"
    assert tool.events.count("done:True") == 1
    assert pipe.inlet.flow == ("pending", "r")


@pytest.mark.asyncio
async def test_cancel_before_start_neither_starts_nor_records():
    tool, pipe = _wired()
    task = tool.trigger()
    task.cancel()  # before the task ever ran a step
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)
    assert tool.events == []
    assert pipe.inlet.flow == ("pending",)


@pytest.mark.asyncio
@pytest.mark.parametrize("cls", [Tool, ToolButton, SetTool])
async def test_state_only_tools_reject_trigger_before_scheduling(cls):
    tool = cls()
    starts, dones = [], []
    tool.on_start(starts.append)
    tool.on_done(dones.append)
    with pytest.raises(NotImplementedError, match="does not implement run"):
        tool.trigger()
    await asyncio.sleep(0)
    assert tool._task is None
    assert (starts, dones) == ([], [])


def test_tool_button_calls_on_click_with_the_tool():
    seen = []
    tool = ToolButton(on_click=seen.append)
    tool.ui.click()
    assert seen == [tool]


def test_toolbar_on_close_receives_the_toolbar():
    seen = []
    toolbar = Toolbar()
    assert toolbar.close_btn.layout.visibility == "hidden"
    toolbar.on_close = seen.append
    assert toolbar.close_btn.layout.visibility == "visible"
    toolbar.close_btn.click()
    assert seen == [toolbar]
    with pytest.raises(T.TraitError):
        toolbar.on_close = "not callable"


def test_set_tool_observer_is_private():
    assert callable(SetTool._update_active)
    with pytest.raises(DeprecatedAPIError):
        _ = SetTool().handler  # the observer no longer shadows the removed name


# -- removed names: hard errors throughout 3.x ---------------------------------

ON_RUN_WORDS = ("AFTER a successful run", "on_start", "on_done", "success only")


def _assert_on_run_error(err: DeprecatedAPIError):
    message = str(err)
    for words in ON_RUN_WORDS:
        assert words in message, (words, message)
    assert "3.x" in message


@pytest.mark.parametrize("cls", [Tool, ToolButton])
def test_on_run_registration_call_raises_and_registers_nothing(cls):
    tool = cls()
    calls = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a mere DeprecationWarning must not pass
        with pytest.raises(DeprecatedAPIError) as info:
            tool.on_run(calls.append)
    _assert_on_run_error(info.value)
    tool._on_start_handlers(tool)  # nothing was registered on the real dispatcher
    assert calls == []


def test_on_done_assignment_and_constructor_raise_and_register_nothing():
    calls = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(DeprecatedAPIError, match=r"on_done\(callback\)") as info:
            Tool().on_done = calls.append
        assert "3.x" in str(info.value)
        with pytest.raises(DeprecatedAPIError, match=r"on_done\(callback\)"):
            Tool(on_done=calls.append)
    tool = Tool()
    tool._on_done_handlers(tool)
    assert calls == []


def test_on_run_assignment_and_constructor_raise():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(DeprecatedAPIError) as info:
            Tool().on_run = print
        _assert_on_run_error(info.value)
        with pytest.raises(DeprecatedAPIError) as info:
            Tool(on_run=print)
        _assert_on_run_error(info.value)


@pytest.mark.parametrize("cls", [Tool, ToolButton])
def test_handler_raises_on_read_assignment_and_constructor(cls):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(DeprecatedAPIError, match="trigger"):
            _ = cls().handler
        with pytest.raises(DeprecatedAPIError, match="on_click"):
            cls().handler = print
        with pytest.raises(DeprecatedAPIError, match=r"removed in ipyelk 3\.0"):
            cls(handler=print)


def test_removed_names_keep_class_introspection_working():
    # class-level access is what Sphinx autodoc and ``inspect`` do: it must not raise
    assert isinstance(Tool.handler, RemovedAPI)
    assert isinstance(Tool.on_run, RemovedAPI)
    assert "3.x" in Tool.on_run.__doc__
    assert {"handler", "on_run", "trigger", "on_start"} <= set(dir(Tool))
    assert "handler" not in Tool.class_trait_names()
