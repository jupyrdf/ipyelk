# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import math
from collections import namedtuple
from typing import Annotated

from pydantic import (
    BeforeValidator,
    PlainSerializer,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    WrapSerializer,
)
from typing_extensions import TypeAlias

Sentinel = namedtuple("Sentinel", [])
EMPTY_SENTINEL = Sentinel


def elk_option_value(value: object) -> object:
    """Write a ``bool`` or a number as the string ELK reads, keep anything else.

    A whole-number ``float`` below ``2**53`` in magnitude loses its fraction
    (``2.0`` -> ``"2"``), because ELK's integer parser rejects ``"2.0"`` and then
    ignores the option. A larger ``float`` keeps its exponent form
    (``1e16`` -> ``"1e+16"``): its digits are not exact, and ELK's integer
    options cannot hold it.
    """
    if isinstance(value, bool):  # before ``int``: ``bool`` is an ``int``
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"ELK cannot read the layout option value {value!r}")
        if value.is_integer() and abs(value) < 2**53:  # every such integer is exact
            return str(int(value))
        return repr(value)
    if isinstance(value, int):
        return str(value)
    return value


def serialize_layout_options(options: dict, handler: SerializerFunctionWrapHandler):
    """Serialize a ``LayoutOptions`` dictionary, but not a ``None`` value.

    :raises ValueError: for a ``None`` value, which the ELK importer cannot read
    """
    data = handler(options)
    for key, value in data.items():
        if value is None:
            raise ValueError(
                f"layoutOptions[{key!r}] is None: ELK cannot read it. "
                "Delete the key to unset the option."
            )
    return data


#: ELK layout options: option ids to values, both strings. Validation (on pydantic
#: elements) writes ``bool`` and number values as strings and rejects other types.
#: Serialization writes them as strings too, because a value set in place on the
#: dictionary skips validation, and raises ``ValueError`` for a ``None`` value.
LayoutOptions: TypeAlias = Annotated[
    dict[
        str,
        Annotated[
            str,
            BeforeValidator(elk_option_value),
            PlainSerializer(elk_option_value, return_type=object),
        ],
    ],
    WrapSerializer(serialize_layout_options),
]


def serialize_value(data: dict, key: str, value, info: SerializationInfo) -> None:
    """Add a derived ELK value while respecting the caller's field selection."""
    if info.include is not None and key not in info.include:
        return
    if info.exclude is not None:
        if isinstance(info.exclude, set) and key in info.exclude:
            return
        if isinstance(info.exclude, dict):
            excluded = info.exclude.get(key)
            if excluded is True or excluded is Ellipsis:
                return
    if value is None and info.exclude_none:
        data.pop(key, None)
    else:
        data[key] = value


class CounterContextManager:
    counter = 0
    active: bool = False

    def __enter__(self):
        if self.counter == 0:
            self.active = True
        self.counter += 1
        return self

    def __exit__(self, *exc):
        if self.counter == 1:
            self.active = False
        if self.counter >= 1:
            self.counter -= 1
