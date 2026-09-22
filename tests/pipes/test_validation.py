# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``ValidationPipe`` reports once when there is nothing to fix.

Reporting walks every element and every edge; running it a second time only
tells us something new if ``apply_fixes`` moved or added something.  The outlet
index is still rebuilt either way -- it is what downstream pipes read, and it is
where assigned ids get pinned.
"""

import asyncio
import logging

import pytest

from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget, ValidationPipe


@pytest.fixture
def counted_reports(monkeypatch):
    """Count ``get_reports`` calls without changing what it does."""
    calls = []
    original = ValidationPipe.get_reports

    def counting(self, index):
        calls.append(index)
        return original(self, index)

    monkeypatch.setattr(ValidationPipe, "get_reports", counting)
    return calls


def clean_hierarchy() -> tuple[Node, Node, Node, Node]:
    """Ids everywhere, no orphans, every edge already owned by its LCA."""
    root = Node(id="root")
    group = root.add_child(Node(id="group"))
    a = group.add_child(Node(id="a"))
    b = group.add_child(Node(id="b"))
    other = root.add_child(Node(id="other"))
    group.add_edge(a, b).id = "inside"
    root.add_edge(a, other).id = "across"
    return root, group, a, b


def test_second_report_only_after_fixes(counted_reports):
    """Nothing to fix: one report.  Something fixed: the outlet is re-reported."""
    root, group, a, b = clean_hierarchy()
    pipe = ValidationPipe()
    pipe.inlet = MarkElementWidget(value=root)

    asyncio.run(pipe.run())

    assert len(counted_reports) == 1, "a valid hierarchy is reported on once"
    assert pipe.errors == {}
    assert pipe.outlet.value is root
    assert pipe.outlet.index.elements is not None, "the outlet index is still built"
    assert pipe.outlet.index.elements.get("a") is a

    # the same hierarchy, with one edge hung off the wrong node
    counted_reports.clear()
    misowned = root.add_edge(a, b)
    misowned.id = "misowned"

    asyncio.run(pipe.run())

    assert len(counted_reports) == 2, "a fix needs the outlet re-reported"
    assert pipe.errors == {}
    assert misowned in group.edges, "the edge moved to the lowest common ancestor"
    assert misowned not in root.edges

    # and now that it has been fixed, the next run is back to a single report
    counted_reports.clear()
    asyncio.run(pipe.run())
    assert len(counted_reports) == 1


def test_assigning_ids_counts_as_a_fix(counted_reports):
    """``fix_null_id`` mutates the hierarchy, so the outlet is re-reported."""
    root = Node(children=[Node()])
    pipe = ValidationPipe()
    pipe.inlet = MarkElementWidget(value=root)

    asyncio.run(pipe.run())

    assert len(counted_reports) == 2
    assert pipe.errors == {}
    assert root.id
    assert root.children[0].id


def test_orphan_adoption_counts_as_a_fix(counted_reports):
    """An adopted orphan changes the hierarchy the outlet index is built from."""
    root = Node(id="root")
    a = root.add_child(Node(id="a"))
    stray = Node(id="stray")
    root.add_edge(a, stray).id = "e"

    pipe = ValidationPipe()
    pipe.inlet = MarkElementWidget(value=root)

    asyncio.run(pipe.run())

    assert len(counted_reports) == 2
    assert pipe.errors == {}
    assert stray in root.children


@pytest.mark.asyncio
async def test_swapped_browser_copy_is_validated_from_the_indexed_root(caplog):
    """A caller that still swaps ``inlet.value = outlet.value`` (2.1.x
    ``Diagram.refresh``) keeps object identity and hidden elements (#164).
    """
    from ipyelk.elements import NodeProperties

    hidden = Node(id="hidden", properties=NodeProperties(hidden=True))
    a = Node(id="a", children=[hidden])
    root = Node(id="root", children=[a])
    pipe = ValidationPipe()
    pipe.inlet = MarkElementWidget(value=root)
    await pipe.run()

    # a browser roundtrip on a downstream outlet sharing the index ...
    outlet = MarkElementWidget(index=pipe.inlet.index)
    wire = root.model_dump(mode="json", exclude_none=True)
    wire["children"][0]["x"] = 10.0
    outlet.set_state({"value": wire})
    outlet.persist()
    assert a.x == pytest.approx(10.0), "persist put the geometry on the user's node"
    # ... and then the old swap
    pipe.inlet.value = outlet.value
    assert pipe.inlet.value is not root

    with caplog.at_level(logging.WARNING, logger=pipe.log.name):
        await pipe.run()

    assert "browser copy" in caplog.text
    assert pipe.inlet.value is root, "the inlet is back on the user's tree"
    assert pipe.outlet.value is root
    elements = pipe.inlet.index.elements
    assert elements.get("a") is a
    assert elements.get("hidden") is hidden
    assert pipe.errors == {}


@pytest.mark.asyncio
async def test_new_inlet_value_is_not_mistaken_for_a_swap(caplog):
    """Assigning a fresh tree -- even one reusing every id -- replaces the root."""
    root = Node(id="root", children=[Node(id="a")])
    pipe = ValidationPipe()
    pipe.inlet = MarkElementWidget(value=root)
    await pipe.run()

    new_a = Node(id="a")
    new_root = Node(id="root", children=[new_a])
    pipe.inlet.value = new_root
    with caplog.at_level(logging.WARNING, logger=pipe.log.name):
        await pipe.run()

    assert "browser copy" not in caplog.text
    assert pipe.inlet.value is new_root
    assert pipe.inlet.index.elements.get("a") is new_a
