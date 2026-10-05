# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from collections import namedtuple
from typing import Annotated

from pydantic import BeforeValidator, SerializationInfo
from typing_extensions import TypeAlias

Sentinel = namedtuple("Sentinel", [])
EMPTY_SENTINEL = Sentinel


def elk_option_value(value: object) -> object:
    """Write a ``bool`` or a number as the string ELK reads, keep anything else."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return value


#: ELK layout options: option ids to values, both strings. Validation (on pydantic
#: elements) writes ``bool`` and number values as strings and rejects other types.
LayoutOptions: TypeAlias = dict[str, Annotated[str, BeforeValidator(elk_option_value)]]


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
