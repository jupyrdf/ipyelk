"""The layout options, algorithms and categories of the bundled ``elkjs``."""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).parent / "elk-catalog.json"


@lru_cache(maxsize=1)
def elk_catalog() -> dict[str, Any]:
    """Read ``elk-catalog.json`` once."""
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _option_ids() -> frozenset[str]:
    return frozenset(option["id"] for option in elk_catalog()["options"])


@lru_cache(maxsize=1024)
def _is_known(key: str) -> bool:
    ids = _option_ids()
    return key in ids or sum(i.endswith(f".{key}") for i in ids) == 1


def unknown_layout_options(keys: Iterable[str]) -> list[str]:
    """Return the layout option keys that ELK does not resolve to one option.

    ELK takes a full id, such as ``org.eclipse.elk.direction``, or the end of one
    that starts after a dot, such as ``elk.direction`` or ``spacing.nodeNode``. ELK
    ignores a key that ends no id. A key that ends more than one id can set a
    different option: ``direction`` also ends
    ``org.eclipse.elk.layered.priority.direction``. ELK reports neither case.

    :param keys: layout option keys, or a ``LayoutOptions`` dictionary
    :return: the keys that are unknown or ambiguous, in their order
    """
    return [key for key in keys if not _is_known(key)]
