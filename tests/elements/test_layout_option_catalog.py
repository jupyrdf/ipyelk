"""Check the hand-written layout options against the ELK option catalog."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import importlib
import json
import pkgutil
from collections.abc import Iterator
from pathlib import Path

import pytest

import ipyelk.schema
from ipyelk.elements import layout_options
from ipyelk.elements.layout_options import port_options
from ipyelk.elements.layout_options.layout import ALGORITHM_OPTIONS, Algorithm
from ipyelk.elements.layout_options.model import ElkEdge, ElkLabel, ElkNode, ElkPort
from ipyelk.elements.layout_options.selection_widgets import LayoutOptionWidget

CATALOG = json.loads(
    (Path(ipyelk.schema.__file__).parent / "elk-catalog.json").read_text(
        encoding="utf-8"
    )
)
OPTIONS = {option["id"]: option for option in CATALOG["options"]}
ALGORITHMS = {algorithm["id"] for algorithm in CATALOG["algorithms"]}

#: how an ``applies_to`` entry maps to an ELK ``targets`` entry
TARGETS = {
    "parents": "PARENTS",
    "nodes": "NODES",
    ElkNode: "NODES",
    ElkEdge: "EDGES",
    ElkPort: "PORTS",
    ElkLabel: "LABELS",
}

# import every module, so that every subclass is defined
for _module in pkgutil.iter_modules(layout_options.__path__):
    importlib.import_module(f"{layout_options.__name__}.{_module.name}")


def _subclasses(cls: type) -> Iterator[type]:
    for sub in cls.__subclasses__():
        yield sub
        yield from _subclasses(sub)


#: every option class with an ELK id (``OptionsWidget`` is a group, not an option)
OPTION_CLASSES = sorted(
    {cls for cls in _subclasses(LayoutOptionWidget) if isinstance(cls.identifier, str)},
    key=lambda cls: cls.__name__,
)
ALGORITHM_CLASSES = sorted(_subclasses(Algorithm), key=lambda cls: cls.__name__)


def test_catalog_is_not_empty() -> None:
    assert CATALOG["elkjs"]
    assert len(OPTIONS) > 100
    assert len(OPTION_CLASSES) > 50


@pytest.mark.parametrize("cls", OPTION_CLASSES, ids=lambda cls: cls.__name__)
def test_option_identifier_is_known(cls: type[LayoutOptionWidget]) -> None:
    assert cls.identifier == cls.identifier.strip(), "the id has stray whitespace"
    assert cls.identifier in OPTIONS, f"ELK ignores the unknown id {cls.identifier}"


@pytest.mark.parametrize("cls", OPTION_CLASSES, ids=lambda cls: cls.__name__)
def test_option_applies_to_matches_targets(cls: type[LayoutOptionWidget]) -> None:
    option = OPTIONS.get(cls.identifier)
    if option is None:
        pytest.skip(f"{cls.identifier} is not in the catalog")
    applies_to = cls.applies_to
    if not isinstance(applies_to, (list, tuple)):
        applies_to = [applies_to]
    assert sorted({TARGETS[target] for target in applies_to}) == option["targets"]


@pytest.mark.parametrize("cls", ALGORITHM_CLASSES, ids=lambda cls: cls.__name__)
def test_algorithm_is_known(cls: type[Algorithm]) -> None:
    assert cls.identifier in ALGORITHMS, f"elkjs has no algorithm {cls.identifier}"


def test_algorithm_choices_are_known() -> None:
    assert set(ALGORITHM_OPTIONS) <= ALGORITHMS


def test_label_port_spacing_is_split() -> None:
    horizontal = port_options.LabelPortHorizontalSpacing()
    vertical = port_options.LabelPortVerticalSpacing()
    assert horizontal.identifier == "org.eclipse.elk.spacing.labelPortHorizontal"
    assert vertical.identifier == "org.eclipse.elk.spacing.labelPortVertical"
    assert horizontal.value == vertical.value == "1.0"


def test_label_port_spacing_is_deprecated() -> None:
    with pytest.warns(DeprecationWarning, match="LabelPortHorizontalSpacing"):
        option = port_options.LabelPortSpacing(spacing=3)
    assert isinstance(option, port_options.LabelPortHorizontalSpacing)
    assert option.identifier == port_options.LabelPortHorizontalSpacing.identifier
    assert option.value == "3.0"
