"""Test configurationb for ``ipyelk``."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

UTF8 = {"encoding": "utf-8"}

HERE = Path(__file__).parent
ROOT = HERE.parent

PIXI_TOML = ROOT / "pixi.toml"
CI_YML = ROOT / ".github/workflows/ci.yml"
RTD_YML = ROOT / "docs/rtd.yml"
CONTRIB_MD = ROOT / "CONTRIBUTING.md"
CHANGELOG_MD = ROOT / "CHANGELOG.md"
PACKAGE_JSON = ROOT / "package.json"
PYPROJECT_TOML = ROOT / "pyproject.toml"

PIXI_PATTERNS = {
    CI_YML: (4, r"pixi-version: v(.*)"),
    RTD_YML: (1, r"- pixi ==(.*)"),
    CONTRIB_MD: (1, r'"pixi==(.*)"'),
}


@pytest.fixture
def the_pixi_toml() -> dict[str, Any]:
    """Provide the ``pixi.toml``"""
    if not PIXI_TOML.exists():
        pytest.skip("Not in repo")

    try:
        import tomllib
    except ImportError:
        pytest.skip("Running on older python")
        return None

    return tomllib.loads(PIXI_TOML.read_text(**UTF8))


@pytest.fixture
def the_pixi_version(the_pixi_toml: dict[str, Any]) -> str:
    """Provide the source-of-truth version of ``pixi``."""
    return re.findall(r"/v([^/]+)/", the_pixi_toml["$schema"])[0]


@pytest.fixture(params=[str(p.relative_to(ROOT)) for p in PIXI_PATTERNS])
def a_file_with_pixi_versions(request: pytest.FixtureRequest) -> Path:
    """Provide a file that should have ``pixi`` versions."""
    return Path(ROOT / request.param)


@pytest.fixture
def pixi_versions_in_a_file(a_file_with_pixi_versions: Path) -> set[str]:
    """Provide the ``pixi`` versions found in a file."""
    text = a_file_with_pixi_versions.read_text(**UTF8)
    count_pattern = PIXI_PATTERNS.get(Path(a_file_with_pixi_versions))
    assert count_pattern
    count, pattern = count_pattern
    assert pattern
    matches = re.findall(pattern, text)
    assert len(matches) == count
    return set(matches)


@pytest.fixture
def the_changelog_text() -> str:
    if not CHANGELOG_MD.exists():
        pytest.skip("Not in repo")
    return CHANGELOG_MD.read_text(**UTF8)


@pytest.fixture
def the_js_version() -> str:
    return json.loads(PACKAGE_JSON.read_text(**UTF8))["version"]


@pytest.fixture
def the_py_version() -> str:
    try:
        import tomllib
    except ImportError:
        pytest.skip("Running on older python")
        return None

    return tomllib.loads(PYPROJECT_TOML.read_text(**UTF8))["project"]["version"]
