# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``ValidationPipe`` reports once when there is nothing to fix.

Reporting walks every element and every edge; running it a second time only
tells us something new if ``apply_fixes`` moved or added something.  The outlet
index is still rebuilt either way -- it is what downstream pipes read, and it is
where assigned ids get pinned.
"""

import asyncio

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
