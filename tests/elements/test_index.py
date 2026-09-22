# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Node, NodeProperties, Registry
from ipyelk.elements.index import ElementIndex, IDReport, VisIndex, iter_visible


def test_id_report_message_interpolates_duplicated_ids():
    node = Node(id="dup")
    report = IDReport(duplicated={"dup": [node]})
    message = report.message()
    assert "dup" in message
    assert "{eid}" not in message


def test_id_report_message_interpolates_null_ids():
    node = Node()
    report = IDReport(null_ids=[node])
    message = report.message()
    assert "{el}" not in message
    assert str(node) in message


def test_element_index_rejects_unresolved_missing_id():
    root = Node(children=[Node(children=[Node()])])
    with pytest.raises(ValueError, match="without an id") as excinfo:
        ElementIndex.from_els(root)
    # the message names the element type, not the (recursive) element repr
    assert str(excinfo.value).startswith("Cannot index element without an id (Node)")
    assert "children" not in str(excinfo.value)


def test_element_index_keeps_registry_generated_ids():
    node = Node()
    with Registry():
        index = ElementIndex.from_els(node)
        node_id = node.get_id()
        assert node_id is not None
    assert len(index.elements) == 1
    assert index.elements[node_id] is node


def test_vis_index_keeps_registry_generated_ids():
    root = Node(children=[Node(properties=NodeProperties(hidden=True))])
    hidden = root.children[0]
    with Registry():
        index = VisIndex.from_els(root)
        hidden_id = hidden.get_id()
        root_id = root.get_id()
        assert hidden_id is not None
        assert root_id is not None
    assert hidden_id in index.hidden
    assert index.last_visible[hidden_id] == root_id


def _compound_with_hidden_middle_child():
    """``C[x, y(hidden), w]``: the hidden child sits between two visible ones."""
    root = Node(id="root")
    compound = root.add_child(Node(id="C"))
    compound.add_child(Node(id="x"))
    compound.add_child(Node(id="y", properties=NodeProperties(hidden=True)))
    compound.add_child(Node(id="w"))
    return root, compound


def test_iter_visible_does_not_leak_hidden_to_siblings():
    root, compound = _compound_with_hidden_middle_child()
    x, y, w = compound.children
    visited = {el.id: (el, hidden, last) for el, hidden, last in iter_visible(root)}
    assert visited["y"] == (y, True, compound)
    # `w` follows the hidden sibling: not hidden, and its nearest visible element
    # is itself, not `x` (the preceding visible sibling)
    assert visited["w"] == (w, False, w)
    assert visited["x"] == (x, False, x)
    assert visited["C"] == (compound, False, compound)
    assert [el.id for el, hidden, _ in iter_visible(root) if hidden] == ["y"]


def test_vis_index_last_visible_is_the_parent():
    root, _compound = _compound_with_hidden_middle_child()
    index = VisIndex.from_els(root)
    assert index.last_visible["y"] == "C"
    assert "w" not in index.hidden
    assert "x" not in index.hidden
    assert set(index.hidden) == {"y"}
