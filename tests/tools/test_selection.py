# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Selection`` resolves ids strictly by default and tolerantly on request."""

import pytest

from ipyelk.elements import Node
from ipyelk.exceptions import NotFoundError
from ipyelk.pipes import Pipe
from ipyelk.tools import Selection


def _selection(*ids: str) -> Selection:
    pipe = Pipe()
    pipe.inlet.value = Node(id="root", children=[Node(id="n1"), Node(id="n2")])
    return Selection(tee=pipe, ids=ids)


def test_strict_by_default_raises_naming_the_unknown_id():
    sel = _selection("n1", "gone")
    with pytest.raises(NotFoundError, match="gone"):
        list(sel.elements())
    assert sel.ids == ("n1", "gone")  # requested ids are never discarded


def test_tolerant_resolution_skips_unknown_ids_and_reports_them():
    sel = _selection("n1", "gone", "n2", "also-gone")
    assert [el.id for el in sel.elements(strict=False)] == ["n1", "n2"]
    assert sel.missing_ids() == ("gone", "also-gone")


def test_all_known_ids_resolve_in_order_with_nothing_missing():
    sel = _selection("n2", "n1")
    assert [el.id for el in sel.elements()] == ["n2", "n1"]
    assert sel.missing_ids() == ()


def test_selection_before_any_value_is_indexed():
    sel = Selection(tee=Pipe(), ids=("n1",))
    assert sel.missing_ids() == ("n1",)
    assert list(sel.elements(strict=False)) == []
    with pytest.raises(ValueError, match="no elements"):
        list(sel.elements())


def test_ids_is_the_synced_channel_the_browser_writes():
    assert Selection().trait_metadata("ids", "sync") is True


def test_unattached_selection_names_the_problem():
    with pytest.raises(ValueError, match="not attached to a pipe"):
        list(Selection(ids=("n1",)).elements())
