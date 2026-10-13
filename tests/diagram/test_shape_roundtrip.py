# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A typed shape and the user's size survive the real pipeline (#201).

The browser stages are stubbed as in ``test_no_inlet_swap.py``: both echo the
graph back the way ELK treats a leaf (its size is kept), the layout stage also
records every node size it was sent.
"""

from __future__ import annotations

import asyncio

import pytest

from ipyelk import Diagram
from ipyelk.elements import Node, NodeProperties, shapes
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes import flows as F
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer


def _browser_stage(sent: list | None = None):
    async def run(self):
        self.send({"action": "run"})
        wire = self.inlet.value.model_dump(mode="json", exclude_none=True)
        if sent is not None:
            sent.append({n["id"]: (n["width"], n["height"]) for n in wire["children"]})
        self.outlet.set_state({"value": wire})
        self.outlet.persist()

    return run


async def settle(diagram: Diagram):
    task = diagram.pipe._task
    assert task is not None, "no run scheduled"
    await task
    for _ in range(3):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_shape_and_user_size_through_the_pipeline(monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr(BrowserTextSizer, "run", _browser_stage())
    monkeypatch.setattr(ElkJS, "run", _browser_stage(sent))
    circle = shapes.Circle(radius=6)
    round_node = Node(id="round", properties=NodeProperties(shape=circle))
    sized = Node(
        id="sized", width=100, height=50, properties=NodeProperties(shape=circle)
    )
    root = Node(id="root", children=[round_node, sized])
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    assert diagram.pipe.status.exception is None
    assert sent == [{"round": (12, 12), "sized": (100, 50)}]
    assert round_node.properties.shape is circle
    assert (round_node.width, round_node.height) == (12, 12)

    circle.radius = 20
    diagram.source.record(F.Layout)  # a size change needs a new projection
    diagram.refresh()
    await settle(diagram)
    assert diagram.pipe.status.exception is None
    assert sent[-1] == {"round": (40, 40), "sized": (100, 50)}
    assert (round_node.width, round_node.height) == (40, 40)
    diagram.close()
