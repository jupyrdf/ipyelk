# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""A ``Document`` owns the ids of one element tree (#160)."""

import pytest

from ipyelk.elements import (
    Document,
    Label,
    Node,
    NodeProperties,
    Port,
    Resolved,
    iter_elements,
)
from ipyelk.exceptions import NotFoundError
from ipyelk.pipes import VisibilityPipe


def test_index_pins_the_wire_id_of_every_idless_element():
    root = Node(id="r", children=[Node(ports=[Port()], labels=[Label(text="a")])])
    wire = {el.wire_id() for el in iter_elements(root)}
    doc = Document(root)
    assert {el.id for el in iter_elements(root)} == wire
    assert set(doc.elements.elements) == wire
    port = root.children[0].ports[0]
    assert port.id.startswith(f"{root.children[0].id}.")


def test_index_without_assigning_leaves_ids_alone():
    root = Node(children=[Node()])
    doc = Document()
    doc.index(root, assign_ids=False)
    assert root.id is None
    assert doc.resolve(root.wire_id()) == Resolved(root)


def test_resolve_missing_and_lookup():
    root = Node(id="r", children=[Node(id="a"), Node(id="b")])
    a, b = root.children
    doc = Document(root)
    assert doc.resolve("a") == Resolved(a, via_slack=False)
    assert doc.resolve("nope") is None
    assert doc.missing(["a", "nope", "b", "gone"]) == ("nope", "gone")
    assert list(doc.lookup(["b", "a"])) == [b, a]
    assert list(doc.lookup(["b", "nope", "a"], strict=False)) == [b, a]
    with pytest.raises(NotFoundError, match="nope"):
        list(doc.lookup(["a", "nope"]))
    assert doc["a"] is a
    with pytest.raises(NotFoundError, match="id:nope not in index"):
        doc["nope"]


def test_an_empty_document_resolves_nothing():
    doc = Document()
    assert doc.elements is None
    assert doc.resolve("a") is None
    assert doc.missing(["a"]) == ("a",)
    with pytest.raises(NotFoundError, match="id:a not in index"):
        doc["a"]


def hidden_child_tree():
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    hidden = compound.add_child(Node(id="h", properties=NodeProperties(hidden=True)))
    shown = root.add_child(Node(id="shown"))
    root.add_edge(hidden, shown).id = "e"
    return root, hidden


@pytest.mark.asyncio
async def test_a_slack_port_has_its_own_id_and_resolves_via_slack():
    root, hidden = hidden_child_tree()
    pipe = VisibilityPipe()
    pipe.inlet.value = root
    pipe.inlet.build_index()
    await pipe.run()

    (port,) = pipe.outlet.value.children[0].ports
    assert port.id == "h.slack", "not the id of the hidden node"
    assert pipe.outlet.value.edges[0].source is port
    doc = pipe.inlet.index.document
    assert doc.slack == {"h.slack": "h"}
    assert doc.resolve("h.slack") == Resolved(hidden, via_slack=True)
    assert doc.resolve("h") == Resolved(hidden, via_slack=False)

    hidden.properties.hidden = False
    await pipe.run()
    assert doc.slack == {}, "a revealed element has no slack port"
    assert doc.resolve("h.slack") is None
    pipe.close()


@pytest.mark.asyncio
async def test_a_slack_id_never_takes_an_id_in_use():
    root, _ = hidden_child_tree()
    root.add_child(Node(id="h.slack"))
    pipe = VisibilityPipe()
    pipe.inlet.value = root
    pipe.inlet.build_index()
    await pipe.run()

    (port,) = pipe.outlet.value.children[0].ports
    assert port.id == "h.slack.slack"
    assert pipe.inlet.index.document.resolve("h.slack").element.id == "h.slack"
    pipe.close()
