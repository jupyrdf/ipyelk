# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Every ``__all__`` in ``ipyelk`` names only what its module defines."""

from pathlib import Path

import pytest

import ipyelk

SRC = Path(ipyelk.__file__).parent
MODULES = sorted(
    ".".join(["ipyelk", *path.relative_to(SRC).with_suffix("").parts]).removesuffix(
        ".__init__"
    )
    for path in SRC.rglob("*.py")
    if "__all__" in path.read_text(encoding="utf-8")
)


def test_modules_are_found():
    assert {"ipyelk", "ipyelk.elements", "ipyelk.elements.layout_options"} <= {*MODULES}


@pytest.mark.parametrize("module", MODULES)
def test_star_import(module: str):
    exec(f"from {module} import *", {})  # ruff: ignore[exec-builtin]
