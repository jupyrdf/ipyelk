# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import pytest

from ipyelk.elements import Node, NodeProperties, Registry
from ipyelk.elements.index import ElementIndex, IDReport, VisIndex


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
    with pytest.raises(ValueError, match="without an id"):
        ElementIndex.from_els(Node())


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
