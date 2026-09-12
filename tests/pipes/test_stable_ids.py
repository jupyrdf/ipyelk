# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Element ids are assigned when the index is built and stay put.

The index's ``Registry`` is the id authority. Building the index writes those ids
onto the elements, so every later serialization -- which happens outside the
Registry -- emits the same ids the index is keyed by. Those ids are the join key
for ``ElementIndex.update`` (hidden elements never reach the wire), browser
selection, and slack ports, which reuse a hidden element's id.
"""

import asyncio
import json

import pytest

from ipyelk.elements import (
    Label,
    Node,
    NodeProperties,
    Port,
    VisIndex,
    convert_elkjson,
    exclude_hidden,
    exclude_layout,
)
from ipyelk.elements.serialization import to_json
from ipyelk.pipes import MarkElementWidget, ValidationPipe


def roundtrip(widget: MarkElementWidget) -> dict:
    """What the browser does: serialize, parse, hand back a new hierarchy."""
    wire = json.loads(json.dumps(to_json(widget.value, None)))
    widget.value = convert_elkjson(json.loads(json.dumps(wire)))
    widget.persist()
    return wire


def test_idless_hierarchy_survives_persist_roundtrips():
    """The documented ``ElementLoader`` path: no explicit ids anywhere."""
    root = Node()
    a = root.add_child(Node(labels=[Label(text="A")]), key="a")
    hidden = a.add_child(Node(properties=NodeProperties(hidden=True)), key="h")
    edge = root.add_edge(a, root)

    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)

    ids = {key: el for key, el in widget.index.elements.items()}
    assert {root.id, a.id, hidden.id, edge.id} <= set(ids)
    assert {el.get_id() for el in ids.values()} == set(ids)

    for _ in range(3):
        wire = roundtrip(widget)
        assert wire["id"] == root.id
        assert wire["children"][0]["id"] == a.id
        assert wire["edges"][0]["id"] == edge.id
        assert wire["edges"][0]["sources"] == [a.id]
        assert wire["edges"][0]["targets"] == [root.id]
        assert not wire["children"][0].get("children"), "hidden child on the wire"

        assert widget.index.root is root
        assert widget.index.elements.get(root.id) is root
        assert widget.index.elements.get(a.id) is a
        assert widget.index.elements.get(edge.id) is edge
        assert widget.index.elements.get(hidden.id) is hidden
        assert widget.value is not root, "the wire hands back a new hierarchy"
        assert widget.value.id == root.id


def test_explicit_ids_are_never_rewritten():
    root = Node(id="r", children=[Node(id="c", ports=[Port(id="c.p")])])
    port = root.children[0].ports[0]
    root.add_edge(port, root).id = "e"

    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    assert [el.id for el in (root, root.children[0], port, root.edges[0])] == [
        "r",
        "c",
        "c.p",
        "e",
    ]

    before = to_json(widget.value, None)
    roundtrip(widget)
    assert to_json(widget.value, None) == before
    assert widget.index.elements.get("c.p") is port


def test_mixed_ids_stay_distinct_and_stable():
    """Explicit and generated ids coexist; generated ones never collide or churn."""
    root = Node(id="r")
    named = root.add_child(Node(id="n"))
    anon = root.add_child(Node())
    anon_port = anon.add_port(Port())
    named.add_port(Port())

    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    generated = {anon.id, anon_port.id, named.ports[0].id}
    assert None not in generated
    assert len(generated) == 3
    assert not generated & {"r", "n"}

    first = to_json(widget.value, None)
    roundtrip(widget)
    assert to_json(widget.value, None) == first


def test_slack_port_keeps_hidden_elements_id_and_object():
    """A slack port comes back from the browser carrying a hidden element's id;
    the hidden element -- not the port -- must stay what that id resolves to.
    """
    root = Node(id="r")
    n1 = root.add_child(Node(id="n1"))
    n2 = root.add_child(Node(id="n2"))
    hidden = n1.add_child(Node(id="h", properties=NodeProperties(hidden=True)))
    root.add_edge(n2, hidden).id = "e"

    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)

    # what `VisibilityPipe` sends: hidden elements collapsed into slack ports
    vis_index = VisIndex.from_els(root)
    with exclude_hidden, exclude_layout:
        data = root.model_dump()
    visible = convert_elkjson(data, vis_index)
    slack = visible.children[0].ports[0]
    assert slack.id == "h"
    assert visible.edges[0].target is slack

    widget.value = convert_elkjson(json.loads(json.dumps(to_json(visible, None))))
    widget.persist()

    assert widget.index.elements.get("h") is hidden
    assert widget.index.elements.get("n1") is n1
    assert widget.index.elements.get("e").target is hidden
    assert widget.index.root is root


def test_validation_pipe_fix_null_id_false_still_rejects_unassigned_ids():
    """``build_index`` pinning ids must not make the strict knob a no-op."""
    root = Node(children=[Node()])
    pipe = ValidationPipe(fix_null_id=False)
    pipe.inlet = MarkElementWidget(value=root)

    with pytest.raises(ValueError, match="Inlet value is not valid"):
        asyncio.run(pipe.run())

    assert set(pipe.errors) == {"Null Id Elements"}
    assert root.id is None
    assert root.children[0].id is None

    pipe.fix_null_id = True
    asyncio.run(pipe.run())
    assert pipe.errors == {}
    assert root.id
    assert root.children[0].id
    assert pipe.inlet.index.elements.get(root.children[0].id) is root.children[0]


def test_new_idless_elements_need_a_rebuild_not_a_merge():
    """Ids are assigned when indexed; the merge path (``persist()``) only accepts
    elements that already have one.  Adding to the Python-side hierarchy means
    rebuilding from it -- same Registry, so existing ids and objects (hidden ones
    included) are kept.
    """
    root = Node()
    a = root.add_child(Node(), key="a")
    hidden = a.add_child(Node(properties=NodeProperties(hidden=True)), key="h")
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    roundtrip(widget)
    before = {key: el for key, el in widget.index.elements.items()}

    new = root.add_child(Node(), key="new")
    widget.value = root
    with pytest.raises(ValueError, match="without an id"):
        widget.persist()
    assert new.id is None

    widget.persist(rebuild_index=True)
    assert new.id
    assert widget.index.elements.get(new.id) is new
    assert {key: el for key, el in widget.index.elements.items()} == {
        **before,
        new.id: new,
    }
    assert widget.index.elements.get(hidden.id) is hidden
    roundtrip(widget)
    assert widget.index.elements.get(new.id) is new
