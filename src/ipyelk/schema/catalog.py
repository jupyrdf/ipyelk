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
def _options_by_id() -> tuple[dict[str, dict], dict[str, dict]]:
    """The options by id, and by the old ids that ELK still accepts."""
    options = elk_catalog()["options"]
    by_legacy_id = {i: o for o in options for i in o.get("legacyIds", ())}
    return {o["id"]: o for o in options}, by_legacy_id


def _ending(by_id: dict[str, dict], key: str) -> list[dict]:
    return [o for i, o in by_id.items() if i.endswith(f".{key}")]


@lru_cache(maxsize=1024)
def _resolve(key: str) -> dict | None:
    """The option that ELK sets for ``key``, or ``None``, in ELK's order of lookup."""
    by_id, by_legacy_id = _options_by_id()
    option = by_id.get(key) or by_legacy_id.get(key)
    if option is not None:
        return option
    # ELK tries the ends of the old ids only when no current id ends with the key
    ending = _ending(by_id, key) or _ending(by_legacy_id, key)
    return ending[0] if len(ending) == 1 else None


def unknown_layout_options(keys: Iterable[str]) -> list[str]:
    """Return the layout option keys that ELK does not resolve to one option.

    ELK takes a full id, such as ``org.eclipse.elk.direction``, or the end of one
    that starts after a dot, such as ``elk.direction`` or ``spacing.nodeNode``. ELK
    ignores a key that ends no id. A key that ends more than one id can set a
    different option: ``direction`` also ends
    ``org.eclipse.elk.layered.priority.direction``. ELK reports neither case.

    ELK also takes the old ids of some options (``legacyIds`` in the catalog), for
    example ``org.eclipse.elk.layered.northOrSouthPort`` for
    ``org.eclipse.elk.layered.allowNonFlowPortsToSwitchSides``, and their ends when
    no current id ends with the key.

    :param keys: layout option keys, or a ``LayoutOptions`` dictionary
    :return: the keys that are unknown or ambiguous, in their order
    """
    return [key for key in keys if _resolve(key) is None]


def untargeted_layout_options(keys: Iterable[str], targets: Iterable[str]) -> list[str]:
    """Return the layout option keys whose option does not apply to ``targets``.

    Each ELK option applies to some kinds of graph element, its ``targets`` in the
    catalog: ``PARENTS`` (a node with children, and the root), ``NODES``,
    ``EDGES``, ``PORTS`` or ``LABELS``. ELK does not report an option set on an
    element of another kind, for example a node option on an edge.

    ipyelk's own label view reads ``org.eclipse.elk.spacing.labelLabel`` from an
    icon label (the first label of a label) for the gap between the icon and the
    text, so the result lists that option on an icon label although ipyelk uses it.

    :param keys: layout option keys, or a ``LayoutOptions`` dictionary
    :param targets: the kinds of the element the keys are set on
    :return: the keys of known options that apply to none of ``targets``, in their
        order (:func:`unknown_layout_options` reports the keys of unknown options)
    """
    targets = set(targets)
    return [
        key
        for key in keys
        if (option := _resolve(key)) is not None
        and targets.isdisjoint(option.get("targets", targets))
    ]
