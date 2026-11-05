"""Failure evidence keeps graph layers distinct without driving the pipeline."""

import asyncio
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipyelk.elements import Edge, Node

probe = runpy.run_path(
    str(Path(__file__).parents[1] / "atest/_resources/fixtures/interactive_probe.py")
)


def mark(identity, edge):
    return SimpleNamespace(
        model_id=identity,
        gen=3,
        value=Node(edges=[Edge(id=edge, source=Node(id="a"), target=Node(id="b"))]),
    )


def pipe(inlet, outlet, task=None):
    return SimpleNamespace(
        model_id="pipe",
        inlet=inlet,
        outlet=outlet,
        _requested=8,
        _generation=7,
        _roundtrip_gen=6,
        _task=task,
        status=SimpleNamespace(exception=RuntimeError("browser error")),
    )


def test_distinct_source_pipeline_viewer_and_unavailable_reader():
    source, outlet, viewer = [
        mark(name, name + "-edge") for name in ("source", "outlet", "viewer")
    ]
    p = pipe(source, outlet)
    broken = SimpleNamespace(model_id="broken")
    p.pipes = [broken]
    result = probe["diagnostic_layers"](
        SimpleNamespace(
            source=source, pipe=p, view=SimpleNamespace(model_id="view", source=viewer)
        )
    )
    # One real failure can now locate a fault boundary instead of a single count.
    assert result["marks"]["source"]["edges"] == ["source-edge"]
    assert result["marks"]["outlet"]["edges"] == ["outlet-edge"]
    assert result["marks"]["viewer"]["edges"] == ["viewer-edge"]
    assert len(result["marks"]) == 3
    assert result["pipes"][0]["requested"] == 8
    assert result["pipes"][0]["generation"] == 7
    assert result["pipes"][0]["browser_generation"] == 6
    assert "AttributeError" in result["pipes"][1]["unavailable"]
    assert "browser error" in json.dumps(result)


@pytest.mark.asyncio
async def test_pending_cancelled_and_failed_tasks_are_read_without_waiting():
    future = asyncio.get_running_loop().create_future()
    assert probe["_task"](future) == {"done": False, "cancelled": False, "error": None}
    future.cancel()
    assert probe["_task"](future)["cancelled"]
    failed = asyncio.get_running_loop().create_future()
    failed.set_exception(RuntimeError("original task failure"))
    assert probe["_task"](failed)["error"] == "original task failure"


def test_failed_source_reader_still_reports_pipeline_layers(capsys):
    """A bad source is evidence, rather than a reason to lose every layer."""
    sliders = [
        SimpleNamespace(description=name, value=value)
        for name, value in zip(probe["SLIDERS"], (10, 10, 1), strict=True)
    ]
    box = SimpleNamespace(
        children=[SimpleNamespace(children=[SimpleNamespace(children=sliders)])]
    )
    outlet = mark("outlet", "outlet-edge")
    broken = SimpleNamespace(model_id="broken-source", gen=0, value=None)
    elk = SimpleNamespace(
        source=broken,
        pipe=pipe(broken, outlet),
        view=SimpleNamespace(model_id="view", source=outlet),
        observe=lambda *_: None,
    )
    check = probe["watch"](box, elk)
    check("failure", diagnostic=True)
    state = json.loads(capsys.readouterr().out.split(" ", 1)[1])
    assert "unavailable" in state
    assert state["layers"]["marks"]["outlet"]["edges"] == ["outlet-edge"]
