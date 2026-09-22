# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Diagram.refresh`` no longer swaps the laid-out copy into the inlet (#164, item 4).

The inlet keeps the user's own tree; geometry and label sizes reach it through
``outlet.persist()`` and the shared ``MarkIndex``.  The browser stages are
stubbed the way ``scripts/bench_pipeline.py`` does: the stub sends the real
``{"action": "run"}`` message and feeds its answer back through the real
browser -> kernel path (``Widget.set_state`` + ``persist``).
"""

import asyncio

import pytest

from ipyelk import Diagram
from ipyelk.elements import Label, Node, NodeProperties
from ipyelk.pipes import MarkElementWidget, Pipeline, ValidationPipe, VisibilityPipe
from ipyelk.pipes.elkjs import ElkJS
from ipyelk.pipes.text_sizer import BrowserTextSizer
from ipyelk.tools import ToggleCollapsedTool

LABEL_WIDTH = 12.5
LABEL_HEIGHT = 14.0


def _walk(el: dict):
    yield el
    for key in ("children", "ports", "labels", "edges"):
        for child in el.get(key) or []:
            yield from _walk(child)


def _browser_stage(mutate):
    """A ``run`` for a synced pipe that answers like the frontend would."""

    async def run(self):
        self.send({"action": "run"})
        wire = self.inlet.value.model_dump(mode="json", exclude_none=True)
        mutate(wire)
        self.outlet.set_state({"value": wire})
        self.outlet.persist()

    return run


def measure_labels(wire: dict):
    for el in _walk(wire):
        if "text" in el:
            el["width"] = LABEL_WIDTH
            el["height"] = LABEL_HEIGHT


def lay_out(wire: dict):
    for i, el in enumerate(_walk(wire)):
        if "text" not in el:
            el["x"], el["y"] = 10.0 * i, 20.0 * i
            el["width"], el["height"] = 100.0, 50.0


@pytest.fixture
def browser(monkeypatch):
    monkeypatch.setattr(BrowserTextSizer, "run", _browser_stage(measure_labels))
    monkeypatch.setattr(ElkJS, "run", _browser_stage(lay_out))


def user_graph():
    """``a`` holds ``c``; an edge ``c -> b`` becomes a slack port when ``c`` hides."""
    c = Node(id="c", labels=[Label(id="lc", text="C")])
    a = Node(id="a", labels=[Label(id="la", text="A")], children=[c])
    b = Node(id="b", labels=[Label(id="lb", text="B")])
    root = Node(id="root", children=[a, b])
    root.add_edge(c, b).id = "e"
    return root, a, b, c


def hidden_graph():
    """The p4d graph: a node hidden from the start, with an edge (no browser stage)."""
    hidden = Node(id="hidden", properties=NodeProperties(hidden=True))
    a = Node(id="a", labels=[Label(id="la", text="A")], children=[hidden])
    b = Node(id="b")
    root = Node(id="root", children=[a, b])
    root.add_edge(hidden, b).id = "e"
    return root, a, hidden


async def settle(diagram: Diagram):
    """Await the pending run and let ``Diagram.refresh``'s done-callback fire."""
    task = diagram.pipe._task
    assert task is not None, "no run scheduled"
    await task
    for _ in range(3):
        await asyncio.sleep(0)


def count_runs(pipe, runs: list):
    pipe.send = lambda content, *_a, **_k: runs.append(content)


@pytest.mark.asyncio
async def test_inlet_is_user_root_after_refresh(browser):
    root, _a, _b, _c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert diagram.pipe.inlet.value is root
    assert diagram.pipe.inlet.index.root is root
    assert diagram.view.source.value is diagram.pipe.outlet.value
    assert diagram.view.source.value is not root, "the view shows the laid-out copy"

    task = diagram.refresh()
    await settle(diagram)
    assert task.exception() is None
    assert diagram.pipe.inlet.value is root


@pytest.mark.asyncio
async def test_style_change_keeps_identity_and_hidden():
    """p4d inverted: a ``New`` run after a refresh still indexes the user's objects."""
    root, a, hidden = hidden_graph()
    diagram = Diagram(
        source=MarkElementWidget(value=root),
        pipe=Pipeline(pipes=[ValidationPipe(), VisibilityPipe()]),
    )
    await settle(diagram)
    assert diagram.pipe.inlet.value is root

    diagram.style = {" .x": {"color": "red"}}
    await settle(diagram)

    elements = diagram.pipe.inlet.index.elements
    assert diagram.pipe.status.exception is None
    assert elements.get("a") is a
    assert elements.get("hidden") is hidden, "not the slack Port sharing its id"
    assert isinstance(elements.get("hidden"), Node)

    diagram.view.selection.ids = ("a",)
    assert [el is a for el in diagram.view.selection.elements()] == [True]


@pytest.mark.asyncio
async def test_geometry_on_user_objects_after_refresh(browser):
    root, a, b, c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert diagram.pipe.inlet.value is root
    for label in (a.labels[0], b.labels[0], c.labels[0]):
        assert label.width == pytest.approx(LABEL_WIDTH)
        assert label.height == pytest.approx(LABEL_HEIGHT)
    assert a.width == pytest.approx(100.0)
    assert a.x is not None
    assert b.x is not None
    assert a.x != b.x
    assert root.edges[0].sections is None, "the stub routes nothing"


@pytest.mark.asyncio
async def test_collapse_does_not_remeasure(browser):
    root, _a, _b, c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    assert diagram.pipe.status.exception is None
    _valid, sizer, _vis, elk = diagram.pipe.pipes
    sizer_runs, elk_runs = [], []
    count_runs(sizer, sizer_runs)
    count_runs(elk, elk_runs)

    diagram.view.selection.ids = ("a",)
    tool = diagram.get_tool(ToggleCollapsedTool)
    await tool.handler()  # toggles a's children; ``on_done`` refreshes
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert c.properties.hidden is True
    assert sizer_runs == [], "a hidden toggle must not re-measure text"
    assert elk_runs == [{"action": "run"}]
    assert diagram.pipe.inlet.value is root
    assert c.labels[0].width == pytest.approx(LABEL_WIDTH), "sizes persist"
    laid_out_a = next(n for n in diagram.pipe.outlet.value.children if n.id == "a")
    assert laid_out_a.children == [], "c is collapsed out of the laid-out tree"
    assert [p.id for p in laid_out_a.ports] == ["c"], "its edge end is a slack port"
    assert c in diagram.pipe.inlet.index.elements.get("a").children
    assert diagram.pipe.inlet.index.elements.get("c") is c, "not the slack port"
