# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``Mark`` and ``MarkFactory`` are removed in 3.0 with error-only tombstones (#160)."""

import sys

import pytest

from ipyelk.exceptions import DeprecatedImportError


@pytest.mark.parametrize("name", ["Mark", "MarkFactory"])
def test_import_from_the_package_raises(name: str) -> None:
    with pytest.raises(DeprecatedImportError, match=rf"ipyelk\.elements\.{name} was"):
        exec(f"from ipyelk.elements import {name}", {})  # ruff: ignore[exec-builtin]
    import ipyelk.elements

    assert "3.x" in ipyelk.elements._REMOVED[name]
    assert "Node.clone(prefix)" in ipyelk.elements._REMOVED[name]
    assert name not in ipyelk.elements.__all__
    assert name not in dir(ipyelk.elements)


def test_import_of_the_module_raises() -> None:
    sys.modules.pop("ipyelk.elements.mark_factory", None)
    with pytest.raises(DeprecatedImportError, match=r"ipyelk\.from_nx"):
        import ipyelk.elements.mark_factory  # ruff: ignore[unused-import]
    assert "ipyelk.elements.mark_factory" not in sys.modules


def test_an_unknown_name_is_a_plain_attribute_error() -> None:
    import ipyelk.elements

    with pytest.raises(AttributeError) as info:
        _ = ipyelk.elements.NoSuchName
    assert not isinstance(info.value, DeprecatedImportError)
