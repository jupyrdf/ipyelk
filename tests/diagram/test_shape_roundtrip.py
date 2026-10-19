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
from ipywidgets import IntSlider

from ipyelk import Diagram
from ipyelk.elements import Label, LabelProperties, Node, NodeProperties, shapes
from ipyelk.pipes import MarkElementWidget, VisibilityPipe
from ipyelk.pipes import flows as F
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer


def _browser_stage(sent: list | None = None, grow: tuple | None = None):
    async def run(self):
        self.send({"action": "run"})
        wire = self.inlet.value.model_dump(mode="json", exclude_none=True)
        if sent is not None:
            sent.append({n["id"]: (n["width"], n["height"]) for n in wire["children"]})
        if grow is not None:
            for node in wire["children"]:
                node["width"], node["height"] = grow
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


@pytest.mark.asyncio
async def test_a_refresh_without_a_layout_shows_the_laid_out_size(monkeypatch):
    """A refresh that runs no stage hands the user's tree to the view, which
    must show the size the layout gave a node, not the input size.
    """
    monkeypatch.setattr(BrowserTextSizer, "run", _browser_stage())
    monkeypatch.setattr(ElkJS, "run", _browser_stage(grow=(200.0, 150.0)))
    circle = shapes.Circle(radius=6)
    node = Node(id="round", properties=NodeProperties(shape=circle))
    root = Node(id="root", children=[node])
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    assert diagram.pipe.status.exception is None
    assert node.properties.shape is circle
    assert (node.width, node.height) == (200, 150)

    node.add_class("highlight")
    diagram.refresh()
    await settle(diagram)
    assert diagram.pipe.status.exception is None
    assert diagram.view.source.value is root
    shown = diagram.view.source.get_state(key="value")["value"]["children"][0]
    assert (shown["width"], shown["height"]) == (200, 150)
    diagram.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "expected"),
    [
        (Label(id="l", text="Point", width=80), (80, 17)),
        (Label(id="l", text="Point", height=40), (57, 40)),
        (
            Label(
                id="l",
                text="Point",
                properties=LabelProperties(shape=shapes.LabelShape(width=100)),
            ),
            (100, 17),
        ),
    ],
)
async def test_label_input_size_wins_over_measurement_from_the_first_layout(
    monkeypatch, label, expected
):
    sent = []

    async def measure(self):
        wire = self.inlet.value.model_dump(mode="json", exclude_none=True)
        wire["children"][0]["labels"][0].update(width=57, height=17)
        self.outlet.set_state({"value": wire})
        self.outlet.persist()

    async def layout(self):
        wire = self.inlet.value.model_dump(mode="json", exclude_none=True)
        sent.append((
            wire["children"][0]["labels"][0]["width"],
            wire["children"][0]["labels"][0]["height"],
        ))
        self.outlet.set_state({"value": wire})
        self.outlet.persist()

    monkeypatch.setattr(BrowserTextSizer, "run", measure)
    monkeypatch.setattr(ElkJS, "run", layout)
    root = Node(id="root", children=[Node(id="child", labels=[label])])
    diagram = Diagram(source=MarkElementWidget(value=root))
    try:
        await settle(diagram)
        assert diagram.pipe.status.exception is None
        assert sent == [expected]
        assert (label.width, label.height) == expected

        label.text = "A longer label"
        diagram.source.record(F.Layout)
        diagram.refresh()
        await settle(diagram)
        assert diagram.pipe.status.exception is None
        assert sent == [expected, expected]
        assert (label.width, label.height) == expected
    finally:
        diagram.close()


@pytest.mark.asyncio
async def test_a_closed_widget_shape_does_not_break_the_next_run(monkeypatch):
    """The node of a closed widget renders as a ``NodeShape`` (#241)."""
    monkeypatch.setattr(BrowserTextSizer, "run", _browser_stage())
    monkeypatch.setattr(ElkJS, "run", _browser_stage())
    slider = IntSlider()
    node = Node(id="a", properties=NodeProperties(shape=shapes.Widget(widget=slider)))
    root = Node(id="root", children=[node])
    source = MarkElementWidget(value=root)
    source.persist(rebuild_index=True)
    model_id = slider.model_id
    slider.close()
    match = f"model_id {model_id!r}"
    with pytest.warns(UserWarning, match=match):
        await VisibilityPipe(inlet=source).run()
    diagram = Diagram(source=source)
    with pytest.warns(UserWarning, match=match) as record:
        await settle(diagram)
    try:
        assert diagram.pipe.status.exception is None
        assert {str(w.message) for w in record} == {str(record[0].message)}
        shown = diagram.view.source.value.children[0].properties.shape
        assert type(shown) is shapes.NodeShape
        assert shown.use == model_id
        assert node.properties.shape.widget is slider, "the user's shape is kept"
    finally:
        diagram.close()
