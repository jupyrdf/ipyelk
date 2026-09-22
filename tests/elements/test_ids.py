# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Ids on the wire are never ``null`` and never churn (jupyrdf/ipyelk#169).

An id-less element serialises with a uuid minted once per object (``wire_id``);
``id`` itself stays ``None`` until the element is indexed, and the index's
``Registry`` adopts the wire id, so the id first serialised is the one the
element keeps.
"""

import asyncio
import copy
import json

import pytest

from ipyelk.elements import ElementIndex, Label, Node, Port, Registry
from ipyelk.pipes import MarkElementWidget, ValidationPipe


def test_idless_node_serialises_a_stable_uuid():
    node = Node()
    first = node.model_dump()
    second = node.model_dump()
    assert first["id"] is not None
    assert first["id"] == second["id"]
    assert "null" not in json.dumps(node.model_dump(mode="json", exclude_none=True))
    nested = Node(children=[Node(children=[Node()])])
    wire = nested.model_dump(mode="json", exclude_none=True)
    assert "null" not in json.dumps(wire)
    assert wire["id"]
    assert wire["children"][0]["id"]
    assert wire["children"][0]["children"][0]["id"]


def test_edge_endpoints_never_null():
    root = Node()
    source = root.add_child(Node())
    target = root.add_child(Node())
    edge = root.add_edge(source, target)
    assert edge.sources == [source.wire_id()]
    assert edge.targets == [target.wire_id()]
    wire = root.model_dump()
    assert wire["edges"][0]["sources"] == [wire["children"][0]["id"]]
    assert wire["edges"][0]["targets"] == [wire["children"][1]["id"]]
    assert None not in wire["edges"][0]["sources"] + wire["edges"][0]["targets"]


def test_port_id_composes_from_explicit_parent_id():
    port = Port()
    node = Node(id="N", ports=[port])
    outside = node.model_dump()["ports"][0]["id"]
    assert outside.startswith("N.")
    assert port.get_id() is None, "no id without a Registry"
    with Registry():
        inside = port.get_id()
        dumped = node.model_dump()["ports"][0]["id"]
    assert inside is not None
    assert inside.startswith("N.")
    assert inside == dumped == outside, "the same port id in and out of a Registry"
    assert port.id is None

    explicit = Node(id="N", ports=[Port(id="p")])
    assert explicit.model_dump()["ports"][0]["id"] == "p"
    with Registry():
        assert explicit.ports[0].get_id() == "p"


def test_wire_id_becomes_the_indexed_id():
    """The id first put on the wire is the id the index assigns: no churn."""
    root = Node()
    child = root.add_child(Node())
    port = child.add_port(Port())
    edge = root.add_edge(port, root)

    widget = MarkElementWidget(value=root)  # serialises at construction
    first_wire = widget.get_state()["value"]
    assert first_wire["id"] is not None
    assert root.id is None, "serialising does not assign ids"

    widget.persist(rebuild_index=True)
    assert root.id == first_wire["id"]
    assert child.id == first_wire["children"][0]["id"]
    assert port.id == first_wire["children"][0]["ports"][0]["id"]
    assert edge.id == first_wire["edges"][0]["id"]
    assert first_wire["edges"][0]["sources"] == [port.id]
    assert port.id.startswith(f"{child.id}.")

    assert widget.get_state()["value"] == first_wire
    elements = widget.index.elements.elements
    assert {el.get_id() for el in elements.values()} == set(elements)
    assert elements[root.id] is root
    assert elements[port.id] is port
    widget.close()


def test_serialisation_does_not_assign_id():
    root = Node(children=[Node()])
    root.model_dump()
    assert root.id is None
    assert root.children[0].id is None
    assert root.get_id() is None

    pipe = ValidationPipe(fix_null_id=False)
    pipe.inlet = MarkElementWidget(value=root)
    with pytest.raises(ValueError, match="Inlet value is not valid"):
        asyncio.run(pipe.run())
    assert set(pipe.errors) == {"Null Id Elements"}
    assert root.id is None
    assert root.children[0].id is None


def test_label_wrap_does_not_share_generated_ids():
    label = Label(text="one two three four five six", width=10)
    lines = label.wrap(width=10)
    assert len(lines) > 1
    assert label.id is None
    assert all(line.id is None for line in lines)
    wire_ids = {line.wire_id() for line in lines}
    assert len(wire_ids) == len(lines)
    assert label.wire_id() not in wire_ids

    root = Node(id="root", children=[Node(id="n", labels=lines)])
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    assert len({line.id for line in lines}) == len(lines)
    assert not widget.index.elements.check_ids().duplicated
    widget.close()


def test_copies_mint_their_own_wire_ids():
    """A copy is a new element: it keeps an explicit ``id``, never the wire id."""
    original = Node()
    original.model_dump()
    copies = [
        copy.copy(original),
        copy.deepcopy(original),
        original.model_copy(),
        original.model_copy(deep=True),
    ]
    assert all(el.id is None for el in copies)
    assert len({el.wire_id() for el in [original, *copies]}) == 5

    explicit = Node(id="keep", ports=[Port(id="p")])
    assert copy.deepcopy(explicit).id == "keep"
    assert copy.deepcopy(explicit).ports[0].id == "p"
    assert explicit.model_copy(deep=True).id == "keep"
    assert copy.copy(explicit).id == "keep"

    first = Node()
    first.model_dump()
    second = copy.deepcopy(first)
    root = Node(children=[first, second])
    wire = root.model_dump()
    assert wire["children"][0]["id"] != wire["children"][1]["id"]
    widget = MarkElementWidget(value=root)
    widget.persist(rebuild_index=True)
    assert first.id == wire["children"][0]["id"]
    assert second.id == wire["children"][1]["id"]
    assert len(widget.index.elements.elements) == 3
    report = widget.index.elements.check_ids()
    assert not report.null_ids
    assert not report.duplicated
    widget.close()


def test_registry_minted_id_becomes_the_wire_id():
    """Index first, serialise later: index keys and wire ids agree."""
    root = Node(children=[Node(ports=[Port()])])
    child = root.children[0]
    port = child.ports[0]
    with Registry():
        index = ElementIndex.from_els(root)
        root_id, child_id, port_id = root.get_id(), child.get_id(), port.get_id()
    assert root.id is None
    assert child.id is None
    assert port.id is None
    wire = root.model_dump()
    assert wire["id"] == root_id
    assert wire["children"][0]["id"] == child_id
    assert wire["children"][0]["ports"][0]["id"] == port_id
    assert port_id.startswith(f"{child_id}.")
    assert set(index.elements) <= {root_id, child_id, port_id}
    assert index.elements[root_id] is root
    with Registry():
        assert root.get_id() == root_id, "a later Registry adopts the wire id"
        assert port.get_id() == port_id
    assert root.model_dump() == wire
