# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from collections import namedtuple
from typing import Dict, List

EMPTY_SENTINEL = namedtuple("Sentinel", [])


def add_excluded_fields(kwargs: Dict, excluded: List) -> Dict:
    """Shim function to help manipulate excluded fields from the `dict`
    method"""

    exclude = kwargs.pop("exclude", None) or set()
    if isinstance(exclude, set):
        for i in excluded:
            exclude.add(i)
    else:
        raise TypeError(f"TODO handle other types of exclude e.g. {type(exclude)}")
    kwargs["exclude"] = exclude
    return kwargs


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
