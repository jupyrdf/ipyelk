"""The browser probe must report background completion and surface task failures."""
# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import asyncio
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

Probe = runpy.run_path(
    str(
        Path(__file__).parent.parent / "atest/_resources/fixtures/hidden_label_probe.py"
    )
)["Probe"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["reveal", "edit_hidden"])
@pytest.mark.parametrize("outcome", ["success", "error", "cancelled"])
async def test_probe_returns_before_completion_and_reports_result(
    action, outcome, capsys
):
    gate = asyncio.get_running_loop().create_future()
    probe = Probe.__new__(Probe)
    probe.diagram = SimpleNamespace(
        pipe=SimpleNamespace(status=SimpleNamespace(exception=None))
    )
    probe.label = SimpleNamespace(text="label", width=42)
    probe.child = SimpleNamespace(properties=SimpleNamespace(hidden=False))

    async def operation():
        await gate
        if outcome == "error":
            raise RuntimeError("layout failed")

    setattr(probe, action, operation)
    getattr(probe, f"start_{action}")()
    probe.report("pending")
    pending = json.loads(capsys.readouterr().out.split(" ", 1)[1])
    assert pending["done"] is False
    assert pending["error"] is None

    if outcome == "cancelled":
        probe.task.cancel()
    else:
        gate.set_result(None)
    result = await asyncio.gather(probe.task, return_exceptions=True)
    probe.report("finished")
    finished = json.loads(capsys.readouterr().out.split(" ", 1)[1])
    assert finished["done"] is True
    assert (
        finished["error"]
        == {"success": None, "error": "layout failed", "cancelled": "cancelled"}[
            outcome
        ]
    )
    assert (result[0] is None) == (outcome == "success")
