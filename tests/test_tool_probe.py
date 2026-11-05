"""Acceptance operations must return the cell and expose background failures."""
# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import asyncio
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

Probe = runpy.run_path(
    str(Path(__file__).parent.parent / "atest/_resources/fixtures/tool_probe.py")
)["Probe"]


def probe_without_widgets():
    probe = Probe.__new__(Probe)
    probe.diagram = SimpleNamespace(
        pipe=SimpleNamespace(status=SimpleNamespace(exception=None))
    )
    probe.operation = "ready"
    probe.task = asyncio.get_running_loop().create_future()
    probe.task.set_result(None)
    return probe


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation", ["relayout", "collapse", "refresh_burst", "headless"]
)
@pytest.mark.parametrize("outcome", ["success", "error", "cancelled"])
async def test_start_returns_before_completion_and_reports_outcome(operation, outcome):
    probe = probe_without_widgets()
    gate = asyncio.get_running_loop().create_future()

    async def work():
        await gate
        if outcome == "error":
            raise RuntimeError("operation failed")

    setattr(probe, operation, work)
    probe.start(operation)
    assert probe.operation_state() == {
        "operation": operation,
        "done": False,
        "cancelled": False,
        "error": None,
    }
    if outcome == "cancelled":
        probe.task.cancel()
    else:
        gate.set_result(None)
    await asyncio.gather(probe.task, return_exceptions=True)
    state = probe.operation_state()
    assert state["done"]
    assert state["cancelled"] == (outcome == "cancelled")
    assert (
        state["error"]
        == {
            "success": None,
            "error": "operation failed",
            "cancelled": "cancelled",
        }[outcome]
    )


@pytest.mark.asyncio
async def test_initial_ready_waits_for_captured_first_layout():
    probe = probe_without_widgets()
    probe.initial_task = asyncio.get_running_loop().create_future()
    probe.elk, probe.text = SimpleNamespace(calls=0), SimpleNamespace(requests=0)
    probe.task = asyncio.create_task(probe.ready())
    await asyncio.sleep(0)
    assert not probe.operation_state()["done"]
    with pytest.raises(RuntimeError, match="Previous operation did not succeed"):
        probe.start("collapse")
    probe.elk.calls = probe.text.requests = 1
    probe.initial_task.set_result(None)
    await probe.task
    assert probe.operation_state()["done"]
    assert probe.operation_state()["error"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["initial", "pipeline", "no-layout", "no-text"])
async def test_initial_and_pipeline_errors_cannot_pass_or_start_next_operation(failure):
    probe = probe_without_widgets()
    probe.initial_task = asyncio.get_running_loop().create_future()
    probe.elk = SimpleNamespace(calls=0 if failure == "no-layout" else 1)
    probe.text = SimpleNamespace(requests=0 if failure == "no-text" else 1)
    if failure == "initial":
        probe.initial_task.set_exception(RuntimeError("first layout failed"))
    else:
        probe.initial_task.set_result(None)
    if failure == "pipeline":
        probe.diagram.pipe.status.exception = RuntimeError("pipeline failed")
    probe.task = asyncio.create_task(probe.ready())
    await asyncio.gather(probe.task, return_exceptions=True)
    assert probe.operation_state()["done"]
    assert probe.operation_state()["error"] is not None
    with pytest.raises(RuntimeError, match="Previous operation did not succeed"):
        probe.start("relayout")
