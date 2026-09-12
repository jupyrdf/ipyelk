# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from collections import namedtuple

from pydantic import SerializationInfo

Sentinel = namedtuple("Sentinel", [])
EMPTY_SENTINEL = Sentinel


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
