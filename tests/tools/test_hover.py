# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import warnings

import pytest
import traitlets as T

from ipyelk.exceptions import DeprecatedAPIError
from ipyelk.tools import Hover


def test_hovered_id_defaults_to_none():
    assert Hover().hovered_id is None


def test_hovered_id_round_trips_a_string_and_clears_to_none():
    hover = Hover()
    seen = []
    hover.observe(lambda change: seen.append(change.new), "hovered_id")
    hover.hovered_id = "n1"
    assert hover.hovered_id == "n1"
    hover.hovered_id = None  # what a pointer leave sends
    assert hover.hovered_id is None
    assert seen == ["n1", None]


@pytest.mark.parametrize("bad", [["n1"], ("n1",), 1])
def test_hovered_id_is_a_single_id_not_a_collection(bad):
    with pytest.raises(T.TraitError):
        Hover(hovered_id=bad)


def test_hovered_id_is_synced_and_ids_is_gone():
    hover = Hover()
    assert hover.trait_metadata("hovered_id", "sync") is True
    assert "ids" not in hover.traits()  # 3.0: removed without an alias


def test_ids_is_a_hard_error_throughout_3x():
    hover = Hover(hovered_id="n1")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # a warning must not pass for compliance
        with pytest.raises(DeprecatedAPIError, match=r"hovered_id") as info:
            _ = hover.ids
        message = str(info.value)
        assert "3.x" in message
        assert "one id" in message  # why: the plural name only ever held one str
        assert "leave" in message  # why: it never cleared on pointer leave
        with pytest.raises(DeprecatedAPIError, match=r"hovered_id"):
            hover.ids = "n2"
        with pytest.raises(DeprecatedAPIError, match=r"hovered_id"):
            Hover(ids="n2")
    assert hover.hovered_id == "n1"  # rejected writes had no side effect
    assert "ids" not in Hover.class_trait_names()  # nothing synced under the old name
    assert Hover.ids.__doc__.startswith("Removed in 3.0")  # class access is docs-safe
