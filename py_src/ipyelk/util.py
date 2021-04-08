# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, List, Optional


def merge(d1: Optional[Dict], d2: Optional[Dict]) -> Optional[Dict]:
    """Merge two dictionaries while first testing if either are `None`.
    The first dictionary's keys take precedence over the second dictionary.
    If the final merged dictionary is empty `None` is returned.

    :param d1: primary dictionary
    :type d1: Optional[Dict]
    :param d2: secondary dictionary
    :type d2: Optional[Dict]
    :return: merged dictionary
    :rtype: Dict
    """
    if d1 is None:
        d1 = {}
    elif not isinstance(d1, dict):
        d1 = d1.to_dict()
    if d2 is None:
        d2 = {}
    elif not isinstance(d2, dict):
        d2 = d2.to_dict()

    cl1 = d1.get("cssClasses", "")
    cl2 = d2.get("cssClasses", "")
    cl = " ".join(sorted(set([*cl1.split(), *cl2.split()]))).strip()

    value = {**d2, **d1}  # right most wins if duplicated keys

    # if either had cssClasses, update that
    if cl:
        value["cssClasses"] = cl

    if value:
        return value


def listed(values: Optional[List]) -> List:
    """Checks if incoming `values` is None then either returns a new list or
    original value.

    :param values: List of values
    :type values: Optional[List]
    :return: List of values or empty list
    :rtype: List
    """
    if values is None:
        return []
    return values
