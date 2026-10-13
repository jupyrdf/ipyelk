"""Layout options are a ``dict[str, str]`` on elements and option widgets."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import json
import re
import warnings
from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from functools import partial

import pytest
from pydantic import ValidationError
from traitlets import TraitError

from ipyelk.elements import Label, Node
from ipyelk.elements import layout_options as opt


def test_node_dump_is_json() -> None:
    node = Node(
        id="n",
        labels=[Label(text="n", layoutOptions={opt.NodeLabelPlacement.identifier: ""})],
        layoutOptions={opt.Direction.identifier: "DOWN"},
    )
    dumped = json.loads(json.dumps(node.model_dump(mode="json")))
    assert dumped["layoutOptions"] == {"org.eclipse.elk.direction": "DOWN"}


def test_options_widget_value_is_strings() -> None:
    widget = opt.OptionsWidget(
        options=[opt.Direction(value="DOWN"), opt.NodeSpacing(spacing=4)]
    )
    assert widget.value == {
        "org.eclipse.elk.direction": "DOWN",
        "org.eclipse.elk.spacing.nodeNode": "4.0",
    }
    with pytest.raises(TraitError):
        widget.value = {"org.eclipse.elk.direction": 1}


def test_bool_and_number_values_become_strings() -> None:
    node = Node(layoutOptions={"elk.spacing.nodeNode": 20, "elk.x": 1.5, "elk.y": True})
    assert node.layoutOptions == {
        "elk.spacing.nodeNode": "20",
        "elk.x": "1.5",
        "elk.y": "true",
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.0, "2"),
        (-3.0, "-3"),
        (1e9, "1000000000"),
        (2.0**53 - 1, "9007199254740991"),
        (0.5, "0.5"),
        # past 2**53 a float's digits are not exact: keep the form `repr` gives it
        (2.0**53, "9007199254740992.0"),
        (1e16, "1e+16"),
        (-1e300, "-1e+300"),
    ],
)
def test_whole_number_floats_lose_the_fraction(value: float, expected: str) -> None:
    # ELK's integer parser rejects "2.0" and then ignores the option
    node = Node(layoutOptions={"org.eclipse.elk.partitioning.partition": value})
    assert node.layoutOptions == {"org.eclipse.elk.partitioning.partition": expected}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(ValidationError, match="ELK cannot read"):
        Node(layoutOptions={"elk.spacing.nodeNode": value})


class WrappedFloat(float):
    """A ``float`` with a decorated ``repr``, like ``numpy.float64`` in ``numpy`` 2."""

    def __repr__(self) -> str:
        return f"WrappedFloat({float(self)!r})"


class WrappedInt(int):
    """An ``int`` with a decorated ``repr``, like ``numpy.int64`` in ``numpy`` 2."""

    def __repr__(self) -> str:
        return f"WrappedInt({int(self)!r})"


class WrappedBool:
    """A stand-in for ``numpy.bool_``, which is found by its type's module and name."""

    __module__ = "numpy"

    def __bool__(self) -> bool:
        return True


WrappedBool.__name__ = "bool"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (WrappedFloat(12.5), "12.5"),
        (WrappedFloat(2.0), "2"),
        (WrappedFloat(1e16), "1e+16"),
        (WrappedInt(7), "7"),
        (WrappedBool(), "true"),
        (Fraction(5, 2), "2.5"),
        (Fraction(4, 2), "2"),
        (Decimal("12.5"), "12.5"),
        (Decimal("2.0"), "2"),
    ],
)
def test_other_number_types_become_strings(value: object, expected: str) -> None:
    # a subclass's `repr` must not reach ELK: `numpy` 2 gives "np.float64(12.5)"
    node = Node(id="n", layoutOptions={"elk.spacing.nodeNode": value})
    assert node.layoutOptions == {"elk.spacing.nodeNode": expected}
    node.layoutOptions["elk.spacing.nodeNode"] = value  # in place: the serializer
    assert node.model_dump()["layoutOptions"] == {"elk.spacing.nodeNode": expected}
    dumped = json.loads(node.model_dump_json())["layoutOptions"]
    assert dumped == {"elk.spacing.nodeNode": expected}


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_decimals_are_rejected(value: Decimal) -> None:
    with pytest.raises(ValidationError, match="ELK cannot read"):
        Node(layoutOptions={"elk.spacing.nodeNode": value})


def test_in_place_values_serialize_as_strings_without_warnings() -> None:
    node = Node(id="n")
    node.layoutOptions["elk.spacing.nodeNode"] = 20
    node.layoutOptions.update({"elk.partitioning.partition": 2.0, "elk.y": False})
    expected = {
        "elk.spacing.nodeNode": "20",
        "elk.partitioning.partition": "2",
        "elk.y": "false",
    }
    with warnings.catch_warnings():
        # pydantic's serializer warnings are a UserWarning
        warnings.simplefilter("error", UserWarning)
        assert node.model_dump()["layoutOptions"] == expected
        assert json.loads(node.model_dump_json())["layoutOptions"] == expected


@pytest.mark.parametrize(
    "dump",
    [Node.model_dump, Node.model_dump_json, partial(Node.model_dump, mode="json")],
    ids=["python", "json", "python-json-mode"],
)
def test_in_place_none_raises_with_the_key(dump: Callable[[Node], object]) -> None:
    # the elkjs importer throws "Severe implementation error" on a `null` value
    parent = Node(id="p", children=[Node(id="n")])
    parent.children[0].layoutOptions["elk.direction"] = None
    message = (
        "layoutOptions['elk.direction'] is None: ELK cannot read it. "
        "Delete the key to unset the option."
    )
    with pytest.raises(ValueError, match=re.escape(message)):
        dump(parent)


@pytest.mark.parametrize(
    "dump",
    [
        partial(Node.model_dump, exclude_none=True),
        lambda node: json.loads(node.model_dump_json(exclude_none=True)),
    ],
    ids=["python", "json"],
)
def test_in_place_none_is_dropped_with_exclude_none(
    dump: Callable[[Node], dict],
) -> None:
    # `exclude_none` drops the key, so ELK uses the option's default
    parent = Node(id="p", children=[Node(id="n", layoutOptions={"elk.x": "1"})])
    parent.children[0].layoutOptions["elk.direction"] = None
    assert dump(parent)["children"][0]["layoutOptions"] == {"elk.x": "1"}


def test_an_excluded_none_does_not_raise() -> None:
    # the check runs after pydantic applies `include` and `exclude` to the keys
    node = Node(id="n", layoutOptions={"elk.direction": "DOWN"})
    node.layoutOptions["elk.spacing.nodeNode"] = None
    dumped = node.model_dump(exclude={"layoutOptions": {"elk.spacing.nodeNode"}})
    assert dumped["layoutOptions"] == {"elk.direction": "DOWN"}


@pytest.mark.parametrize(
    "options",
    [{1: "DOWN"}, {"elk.direction": None}, {"elk.direction": ["DOWN"]}],
    ids=["int-key", "none-value", "list-value"],
)
def test_other_keys_and_values_are_rejected(options: dict) -> None:
    with pytest.raises(ValidationError):
        Node(layoutOptions=options)
    node = Node()
    with pytest.raises(ValidationError):
        node.layoutOptions = options
