# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Dict, List


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
