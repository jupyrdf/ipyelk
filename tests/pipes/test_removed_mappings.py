# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``ipyelk.pipes.mappings`` is removed in 3.0 with an error-only guard (#217)."""

import sys

import pytest

from ipyelk.exceptions import DeprecatedImportError


def test_import_of_the_module_raises() -> None:
    sys.modules.pop("ipyelk.pipes.mappings", None)
    with pytest.raises(DeprecatedImportError, match="nothing replaces them"):
        import ipyelk.pipes.mappings  # ruff: ignore[unused-import]
    assert "ipyelk.pipes.mappings" not in sys.modules


def test_import_from_the_package_raises() -> None:
    with pytest.raises(DeprecatedImportError, match=r"ipyelk\.pipes\.mappings"):
        from ipyelk.pipes import mappings  # ruff: ignore[unused-import]
    import ipyelk.pipes  # the package itself is unaffected

    assert ipyelk.pipes.Pipe
