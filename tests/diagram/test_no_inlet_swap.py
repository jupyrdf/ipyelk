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
from ipyelk.pipes import flows as F
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
    await tool.trigger()  # toggles the children of ``a``; ``on_done`` refreshes
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert c.properties.hidden is True
    assert sizer_runs == [], "a hidden toggle must not re-measure text"
    assert elk_runs == [{"action": "run"}]
    assert diagram.pipe.inlet.value is root
    assert c.labels[0].width == pytest.approx(LABEL_WIDTH), "sizes persist"
    laid_out_a = next(n for n in diagram.pipe.outlet.value.children if n.id == "a")
    assert laid_out_a.children == [], "c is collapsed out of the laid-out tree"
    assert [p.id for p in laid_out_a.ports] == ["c.slack"], (
        "its edge end is a slack port"
    )
    assert c in diagram.pipe.inlet.index.elements.get("a").children
    assert diagram.pipe.inlet.index.elements.get("c") is c, "not the slack port"
    document = diagram.pipe.inlet.index.document
    assert document.resolve("c.slack") == (c, True), "selecting it selects c"
    diagram.view.selection.ids = ("c.slack",)
    assert list(diagram.view.selection.elements()) == [c]


@pytest.mark.asyncio
async def test_a_refresh_after_a_collapse_shows_the_projection(browser):
    """Nothing pending after a collapse: the view keeps the slack port (#231).

    Fit, Center and a new ``diagram.view`` do not refresh, so this is the only path.
    """
    root, _a, _b, _c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    diagram.view.selection.ids = ("a",)
    await diagram.get_tool(ToggleCollapsedTool).trigger()
    await settle(diagram)
    collapsed = diagram.view.source.get_state(key="value")["value"]
    assert collapsed["edges"][0]["sources"] == ["c.slack"]

    diagram.refresh()
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert diagram.view.source.get_state(key="value")["value"] == collapsed
    diagram.close()


def _change_text(diagram: Diagram, b: Node) -> None:
    b.labels[0].text = "B longer"
    diagram.source.record(F.Text.text)


def _record(tag: str):
    def change(diagram: Diagram, _b: Node) -> None:
        diagram.source.record(tag)

    return change


#: runs that measure text again (#246)
REMEASURE = {
    "text": _change_text,
    "layout": _record(F.Layout),
    "new": _record(F.New),
}


def _view(diagram: Diagram) -> dict:
    return diagram.view.source.get_state(key="value")["value"]


def _node(wire: dict, node_id: str) -> dict:
    return next(n for n in wire["children"] if n["id"] == node_id)


async def _collapse_a(diagram: Diagram) -> None:
    diagram.view.selection.ids = ("a",)
    await diagram.get_tool(ToggleCollapsedTool).trigger()
    await settle(diagram)


@pytest.mark.asyncio
@pytest.mark.parametrize("change", REMEASURE.values(), ids=REMEASURE.keys())
async def test_a_run_that_measures_text_after_a_collapse_shows_the_projection(
    browser, change
):
    """The answer of the text sizer has no edge to the hidden ``c``, and the view
    keeps the slack port (#246).
    """
    root, _a, b, c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    await _collapse_a(diagram)
    sizer = diagram.pipe.pipes[1]
    sizer_runs = []
    count_runs(sizer, sizer_runs)

    change(diagram, b)
    diagram.refresh()
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    assert sizer_runs == [{"action": "run"}], "the text is measured again"
    view = _view(diagram)
    assert _node(view, "a").get("children", []) == []
    assert [p["id"] for p in _node(view, "a")["ports"]] == ["c.slack"]
    assert view["edges"][0]["sources"] == ["c.slack"]
    assert _node(view, "b")["labels"][0]["text"] == b.labels[0].text
    assert diagram.pipe.inlet.index.elements.get("c") is c
    diagram.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", REMEASURE.values(), ids=REMEASURE.keys())
async def test_an_expand_after_a_run_that_measures_text_shows_the_child(
    browser, change
):
    """After #246's run, expanding ``a`` brings back ``c`` and its edge."""
    root, _a, b, c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    await _collapse_a(diagram)
    change(diagram, b)
    diagram.refresh()
    await settle(diagram)

    await _collapse_a(diagram)  # toggles ``c`` back

    assert diagram.pipe.status.exception is None
    assert c.properties.hidden is False
    view = _view(diagram)
    a_wire = _node(view, "a")
    assert [n["id"] for n in a_wire["children"]] == ["c"]
    assert a_wire["children"][0]["labels"][0]["width"] == pytest.approx(LABEL_WIDTH)
    assert a_wire.get("ports", []) == []
    assert view["edges"][0]["sources"] == ["c"]
    diagram.close()


@pytest.mark.asyncio
async def test_a_node_hidden_from_the_start_lays_out_with_the_text_sizer(browser):
    """The first run measures text with an edge to a hidden node (#246)."""
    root, _a, _hidden = hidden_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    view = _view(diagram)
    assert [p["id"] for p in _node(view, "a")["ports"]] == ["hidden.slack"]
    assert view["edges"][0]["sources"] == ["hidden.slack"]
    diagram.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("collapse", [False, True], ids=["expanded", "collapsed"])
async def test_a_layout_option_change_reaches_the_layout(monkeypatch, collapse):
    """``VisibilityPipe`` projects again for a change that ``ElkJS`` lays out (#246)."""
    laid_out = []

    def record_and_lay_out(wire: dict) -> None:
        laid_out.append(wire)
        lay_out(wire)

    monkeypatch.setattr(BrowserTextSizer, "run", _browser_stage(measure_labels))
    monkeypatch.setattr(ElkJS, "run", _browser_stage(record_and_lay_out))
    root, a, _b, _c = user_graph()
    diagram = Diagram(source=MarkElementWidget(value=root))
    await settle(diagram)
    if collapse:
        await _collapse_a(diagram)
    padding = "[top=1,left=1,bottom=1,right=1]"

    a.layoutOptions = {"org.eclipse.elk.padding": padding}
    diagram.source.record(F.Node.layout_options)
    diagram.refresh()
    await settle(diagram)

    assert diagram.pipe.status.exception is None
    wire = laid_out[-1]
    assert _node(wire, "a")["layoutOptions"] == {"org.eclipse.elk.padding": padding}
    assert wire["edges"][0]["sources"] == (["c.slack"] if collapse else ["c"])
    diagram.close()
