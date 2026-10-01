# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Tool`` execution lifecycle: trigger/run, on_start, success-only on_done."""

from __future__ import annotations

import asyncio
import inspect
import os
import warnings
from pathlib import Path

import pytest
import traitlets as T

import ipyelk.tools
from ipyelk.elements import Node
from ipyelk.exceptions import DeprecatedAPI, DeprecatedAPIError, RemovedAPI
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
    await asyncio.sleep(0)  # first's cancellation lands; second starts
    assert first.cancelled()
    assert tool.events == ["start:True", "run", "start:True", "run"]
    await asyncio.sleep(0)  # _finished(first) runs one loop turn later
    assert tool._task is second  # stale completion left the new task in place
    assert "done:True" not in tool.events

    tool.gate.set()
    await second
    await asyncio.sleep(0)
    assert tool.events[-1] == "done:True"
    assert tool.events.count("done:True") == 1
    assert tool._task is None
    assert pipe.inlet.flow == ("pending", "r")


@pytest.mark.asyncio
async def test_stale_success_fires_done_but_leaves_the_new_task_in_place():
    """A retrigger between the first run finishing and its done-callback running."""
    tool, pipe = _wired()
    first = tool.trigger()
    await asyncio.sleep(0)
    tool.gate.set()
    await asyncio.sleep(0)  # first's run() returns: the task is done ...
    assert first.done()
    assert not first.cancelled()
    assert tool.events == ["start:True", "run"]  # ... but _finished(first) has not run
    tool.gate.clear()
    second = tool.trigger()  # nothing to cancel; ``first`` is now stale
    assert tool._task is second
    await asyncio.sleep(0)  # _finished(first) runs, second starts
    assert tool.events == ["start:True", "run", "done:True", "start:True", "run"]
    assert tool._task is second  # the stale success did not clear the new task
    assert pipe.inlet.flow == ("pending", "r")

    tool.gate.set()
    await second
    await asyncio.sleep(0)
    assert tool.events.count("done:True") == 2  # one done per success
    assert tool._task is None


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


def test_set_tool_active_observer_moves_the_css_classes():
    n1, n2, n3 = (Node(id=f"n{i}") for i in (1, 2, 3))
    n3.add_class("keep")
    tool = SetTool(css_classes=("active-set", "hl"))
    tool.active = (n1, n2)
    assert {"active-set", "hl"} <= set(n1.properties.cssClasses.split())
    assert {"active-set", "hl"} <= set(n2.properties.cssClasses.split())
    tool.active = (n2, n3)  # n1 departs, n2 stays, n3 enters
    assert not n1.properties.cssClasses
    assert {"active-set", "hl"} <= set(n2.properties.cssClasses.split())
    assert set(n3.properties.cssClasses.split()) == {"keep", "active-set", "hl"}
    tool.active = ()
    assert not n2.properties.cssClasses
    assert n3.properties.cssClasses == "keep"  # only the tool's classes leave
    with pytest.raises(DeprecatedAPIError):
        _ = tool.handler  # the observer no longer shadows the removed name


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


@pytest.mark.parametrize("name", ["on_start", "on_done"])
@pytest.mark.parametrize("cls", [Tool, ToolButton, SetTool])
def test_registration_assignment_and_constructor_raise_and_register_nothing(cls, name):
    calls = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(DeprecatedAPIError, match=rf"{name}\(callback\)") as info:
            setattr(cls(), name, calls.append)
        assert "3.x" in str(info.value)
        with pytest.raises(DeprecatedAPIError, match=rf"{name}\(callback\)"):
            cls(**{name: calls.append})
    tool = cls()
    tool._on_start_handlers(tool)
    tool._on_done_handlers(tool)
    assert calls == []
    # the rejected assignment did not shadow the method on the instance
    getattr(tool, name)(calls.append)
    getattr(tool, f"_{name}_handlers")(tool)
    assert calls == [tool]


@pytest.mark.parametrize("name", ["on_start", "on_done"])
def test_registration_methods_read_like_plain_methods(name):
    # class-level access is what Sphinx autodoc and ``inspect`` do
    func = getattr(Tool, name)
    assert inspect.isfunction(func)
    assert func.__name__ == name
    assert "Register a callback" in func.__doc__
    tool = Tool()
    assert inspect.ismethod(getattr(tool, name))
    assert getattr(tool, name).__self__ is tool
    assert getattr(ToolButton(), name).__func__ is func  # inherited, not copied


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


@pytest.mark.parametrize("cls", [Tool, ToolButton, SetTool])
def test_removed_names_keep_the_attribute_contract_on_instances(cls):
    """``DeprecatedAPIError`` is an ``AttributeError``: duck typing keeps working."""
    tool = cls()
    for name in ("handler", "on_run", "disable"):
        assert isinstance(inspect.getattr_static(cls, name), RemovedAPI)
        assert hasattr(tool, name) is False
        assert getattr(tool, name, "default") == "default"
    assert issubclass(DeprecatedAPIError, AttributeError)


def test_removed_names_survive_inspect_getmembers():
    # ipywidgets' own ``Widget.widgets`` static property breaks ``inspect.getmembers``
    # on any widget instance, so the descriptor contract is checked on a plain class
    class Owner:
        gone = RemovedAPI("Owner.gone was removed")

    members = dict(inspect.getmembers(Owner()))
    assert "gone" not in members
    assert isinstance(dict(inspect.getmembers(Owner))["gone"], RemovedAPI)
    with pytest.raises(DeprecatedAPIError, match="removed"):
        _ = Owner().gone


def test_removed_module_names_keep_their_message_through_from_import():
    """`from ipyelk.tools import Zoom` must show WHY the name went away.

    A module ``__getattr__`` that raises ``AttributeError`` (which
    ``DeprecatedAPIError`` is, for the sake of ``hasattr`` on instances) has its
    message thrown away by the interpreter: ``from module import name`` replaces it
    with a bare ``ImportError("cannot import name ...")``. The module-level
    tombstones therefore raise ``DeprecatedImportError``, which is not an
    ``AttributeError``, and both flavours share ``DeprecatedAPI``.
    """
    import subprocess
    import sys

    src = str(Path(ipyelk.__file__).parent.parent)
    proc = subprocess.run(
        [sys.executable, "-c", "from ipyelk.tools import Zoom"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": src},
    )
    assert proc.returncode != 0
    assert "cannot import name" not in proc.stderr, proc.stderr
    assert "was removed in ipyelk 3.0" in proc.stderr, proc.stderr
    assert "viewer.viewport" in proc.stderr, proc.stderr

    # both flavours are catchable through the shared base
    with pytest.raises(DeprecatedAPI):
        _ = ipyelk.tools.Zoom
    with pytest.raises(DeprecatedAPI):
        _ = Tool().handler
