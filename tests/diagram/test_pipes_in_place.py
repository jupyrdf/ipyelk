# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Changing a pipeline's ``pipes`` in place keeps the ownership rule (#191)."""

from __future__ import annotations

import asyncio

import pytest
import traitlets as T

from ipyelk import Diagram
from ipyelk.diagram.flow import DefaultFlow
from ipyelk.pipes import BrowserTextSizer, Pipe
from ipyelk.pipes.pipeline import Pipeline

from .test_pipe_replacement import (
    is_open,
    live_widgets,
    make_source,
    refresh,
    sizer,
    snapshot,
)

pytestmark = pytest.mark.usefixtures("headless")


@pytest.fixture
def headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IPYELK_NO_BROWSER", "1")


def wiring(diagram: Diagram) -> dict:
    stages = list(diagram.pipe.pipes)
    return {
        **snapshot(diagram),
        "stages": stages,
        "ends": [(p.inlet, p.outlet) for p in stages],
        "owners": [p._diagram() if p._diagram else None for p in stages],
    }


def owner(pipe: Pipe) -> Diagram | None:
    return pipe._diagram() if pipe._diagram else None


@pytest.mark.asyncio
async def test_adding_another_diagrams_stage_is_refused_without_side_effects() -> None:
    first = Diagram(source=make_source())
    second = Diagram(source=make_source())
    await refresh(first)
    await refresh(second)
    nested = Pipeline()
    second.pipe.pipes = [*second.pipe.pipes, nested]
    stage = first.pipe.pipes[1]
    before = (wiring(first), wiring(second), nested.pipes, nested.outlet)
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match="another diagram"):
        second.pipe.pipes = [*second.pipe.pipes, stage]
    with pytest.raises(T.TraitError, match="another diagram"):
        nested.pipes = [stage]

    assert (wiring(first), wiring(second), nested.pipes, nested.outlet) == before
    assert live_widgets() == widgets
    assert owner(stage) is first


def test_adding_a_closed_stage_is_refused() -> None:
    diagram = Diagram(source=make_source())
    closed = Pipe()
    closed.close()
    before = wiring(diagram)
    with pytest.raises(T.TraitError, match="closed"):
        diagram.pipe.pipes = [*diagram.pipe.pipes, closed]
    assert wiring(diagram) == before


def test_a_listed_twice_or_closed_stage_is_refused() -> None:
    diagram = Diagram(source=make_source())
    before = wiring(diagram)
    stage = diagram.pipe.pipes[0]
    with pytest.raises(T.TraitError, match="listed twice"):
        diagram.pipe.pipes = [*diagram.pipe.pipes, stage]
    fresh = Pipe()
    with pytest.raises(T.TraitError, match="listed twice"):
        Pipeline(pipes=[fresh, fresh])
    closed = Pipe()
    closed.close()
    with pytest.raises(T.TraitError, match="closed"):
        Pipeline(pipes=[closed])
    assert wiring(diagram) == before
    assert is_open(fresh)


@pytest.mark.asyncio
async def test_changes_under_held_notifications_keep_owned_stages() -> None:
    """``Widget.set_state`` holds notifications too."""
    diagram = Diagram(source=make_source())
    await refresh(diagram)
    stages = list(diagram.pipe.pipes)
    added = Pipe()

    with diagram.pipe.hold_trait_notifications():
        diagram.pipe.pipes = [*stages, added]
    diagram.pipe.set_state({
        "pipes": [f"IPY_MODEL_{p.model_id}" for p in [*stages, added][::-1]]
    })
    diagram.pipe.pipes = stages

    assert all(owner(p) is diagram for p in stages)
    assert added._diagram is None
    other = Diagram(source=make_source())
    with (
        pytest.raises(T.TraitError, match="another diagram"),
        other.pipe.hold_trait_notifications(),
    ):
        other.pipe.pipes = [*other.pipe.pipes, stages[0]]
    assert owner(stages[0]) is diagram


@pytest.mark.asyncio
async def test_a_stage_removed_mid_run_is_cancelled() -> None:
    diagram = Diagram(source=make_source())
    gate = asyncio.Event()

    class Slow(Pipe):
        async def run(self):
            await gate.wait()

    slow = Slow()
    diagram.pipe.pipes = [*diagram.pipe.pipes, slow]
    task = slow.schedule_run()
    assert task is not None
    await asyncio.sleep(0)

    diagram.pipe.pipes = diagram.pipe.pipes[:-1]
    await asyncio.sleep(0)
    assert task.cancelled()


def test_moving_a_nested_stage_is_refused() -> None:
    inner = DefaultFlow()
    diagram = Diagram(source=make_source(), pipe=Pipeline(pipes=[inner]))
    before = wiring(diagram)
    with pytest.raises(T.TraitError, match="part of the current pipe"):
        diagram.pipe.pipes = [inner, inner.pipes[0]]
    assert wiring(diagram) == before


@pytest.mark.asyncio
async def test_an_added_stage_is_owned_and_styled() -> None:
    diagram = Diagram(source=make_source())
    diagram.style = {" .a": {"fill": "red"}}
    added = BrowserTextSizer()
    nested = Pipeline(pipes=[BrowserTextSizer()])
    diagram.pipe.pipes = [*diagram.pipe.pipes, added, nested]

    for pipe in (added, nested, nested.pipes[0]):
        assert owner(pipe) is diagram
    assert added.style == nested.pipes[0].style == diagram.style
    await refresh(diagram)
    assert nested.outlet.value is not None


@pytest.mark.asyncio
async def test_a_removed_stage_is_released() -> None:
    diagram = Diagram(source=make_source())
    await refresh(diagram)
    removed = sizer(diagram.pipe)
    kept = [p for p in diagram.pipe.pipes if p is not removed]

    diagram.pipe.pipes = kept

    assert removed._diagram is None
    assert is_open(removed)
    assert all(owner(p) is diagram for p in kept)
    assert all(sub is not removed for sub, _ in diagram._pipe_links)
    diagram.style = {" .b": {"fill": "blue"}}
    assert removed.style == {}

    other = Diagram(source=make_source(), pipe=Pipeline(pipes=[removed]))
    assert owner(removed) is other
    assert removed.style == other.style


@pytest.mark.asyncio
async def test_reordering_stages_keeps_them_owned() -> None:
    diagram = Diagram(source=make_source())
    await refresh(diagram)
    stages = list(diagram.pipe.pipes)
    links = list(diagram._pipe_links)

    diagram.pipe.pipes = stages[::-1]
    diagram.pipe.pipes = stages

    assert all(owner(p) is diagram for p in stages)
    assert diagram._pipe_links == links
    diagram.style = {" .c": {"fill": "green"}}
    assert sizer(diagram.pipe).style == diagram.style
    diagram.source.record("again")
    await refresh(diagram)
    assert diagram.view.source.value is not None


@pytest.mark.asyncio
async def test_wrapping_a_live_stage_leaves_it_wired() -> None:
    """``Pipeline(pipes=[...])`` refuses a live stage before rewiring it."""
    c = Diagram(source=make_source())
    await refresh(c)
    stage = c.pipe.pipes[1]
    inlet, outlet = stage.inlet, stage.outlet
    fresh = [Pipe(), Pipeline(pipes=[Pipe()])]
    before = wiring(c)
    widgets = live_widgets()

    with pytest.raises(T.TraitError, match="open diagram"):
        Pipeline(pipes=[stage])
    with pytest.raises(T.TraitError, match="open diagram"):
        Pipeline(pipes=[*fresh, stage])

    assert stage.inlet is inlet
    assert stage.outlet is outlet
    assert wiring(c) == before
    assert live_widgets() == widgets
