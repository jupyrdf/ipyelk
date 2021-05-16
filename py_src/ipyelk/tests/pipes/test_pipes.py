# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, Pipe, Pipeline


@pytest.mark.asyncio
async def test_pipe_run():
    p = Pipe()
    p.inlet = MarkElementWidget()
    await p.run()
    assert p.inlet.value is p.outlet.value


@pytest.mark.asyncio
async def test_pipe_check_dirty():
    f1 = ("a",)
    f2 = ("b",)
    p = Pipe(
        observes=f1,
        reports=f2,
    )
    p.inlet = MarkElementWidget(
        flow=f1,
    )
    assert len(p.outlet.flow) == 0
    assert p.check_dirty()
    assert p.dirty
    assert len(p.outlet.flow) == 2, f"Expected two flow flags. Recieved {p.outlet.flow}"
    # await p.run()
    # assert p.inlet.value is p.outlet.value


@pytest.mark.asyncio
async def test_pipeline_check_dirty():
    f1 = ("a",)
    f2 = ("b",)
    f3 = ("c",)
    p1 = Pipe(
        observes=f1,
        reports=f2,
    )
    p2 = Pipe(
        observes=f3,
        reports=f3,
    )
    p = Pipeline(pipes=(p1, p2))
    assert p.check(), "pipeline should contain no broken pipes"
    p.inlet = MarkElementWidget(
        flow=f1,
        value=Node(),
    )

    # test pipeline with only `p1` dirty
    assert len(p.outlet.flow) == 0
    assert p.check_dirty()
    assert p.dirty
    assert p1.dirty
    assert not p2.dirty
    assert len(p.outlet.flow) == 2, f"Expected two flow flags: `{p.outlet.flow}`"
    assert p.reports == f2, f"Expected pipeline reports to be f2: `{p.reports}`"

    # test pipeline with only `p2` dirty
    p.inlet.flow = f3
    assert p.check_dirty()
    assert p.dirty
    assert not p1.dirty
    assert p2.dirty
    assert len(p.outlet.flow) == 1, f"Expected two flow flags. Recieved {p.outlet.flow}"
    assert p.reports == f3, f"Expected pipeline reports to be f3: `{p.reports}`"

    assert (
        p.inlet.value is not p.outlet.value
    ), "Inlet value should not have propagated yet"
    await p.run()
    assert p.inlet.value is p.outlet.value, "Inlet value should have propagated"
    assert not p.dirty, "Pipeline should not still be dirty"
    assert not p1.dirty, "`p1` should not still be dirty"
    assert not p2.dirty, "`p2` should not still be dirty"
