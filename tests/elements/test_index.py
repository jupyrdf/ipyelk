# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from ipyelk.elements import Node
from ipyelk.elements.index import IDReport


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
