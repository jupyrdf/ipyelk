"""Test configurationb for ``ipyelk``."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any

import ipywidgets.widgets.widget as widget_module
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
README_MD = ROOT / "README.md"

PIXI_PATTERNS = {
    CI_YML: (5, r"pixi-version: v(.*)"),
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
    """Provide the text of the changelog."""
    if not CHANGELOG_MD.exists():
        pytest.skip("Not in repo")
    return CHANGELOG_MD.read_text(**UTF8)


@pytest.fixture
def the_js_version() -> str:
    """Provide the source-of-truth data for the js extension."""
    return json.loads(PACKAGE_JSON.read_text(**UTF8))["version"]


@pytest.fixture
def the_pyproject_data() -> dict[str, Any]:
    """Provide the python project data."""
    try:
        import tomllib
    except ImportError:
        pytest.skip("Running on older python")
        return None

    return tomllib.loads(PYPROJECT_TOML.read_text(**UTF8))


@pytest.fixture
def the_py_version(the_pyproject_data: dict[str, Any]) -> str:
    """Provide the source-of-truth python version."""
    return the_pyproject_data["project"]["version"]


@pytest.fixture
def the_readme_text() -> str:
    if not README_MD.exists():
        pytest.skip("Not in repo")
    return README_MD.read_text(**UTF8)


@pytest.fixture
def kernel_attached_comm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make kernel-side widget sends observable on ipywidgets 8.0.x.

    ipywidgets >= 8.1 opens comms through the ``comm`` package, whose
    no-kernel fallback ``DummyComm`` has no ``kernel`` attribute, so
    ``Widget.notify_change``'s ``getattr(comm, "kernel", True) is not None``
    gate passes and a trait write reaches ``send_state``/``_send``.  8.0.x
    opens an ``ipykernel.comm.Comm`` and gates on ``comm.kernel is not None``:
    with no kernel running, ``kernel`` is ``None`` and a kernel-side write is
    never sent, so a test that captures ``_send`` sees nothing at all.
    ipywidgets' own 8.0 test-suite installs a kernel-attached dummy for the
    same reason; this does the same, and is a no-op on newer builds.  Opt in
    per module (``pytestmark = pytest.mark.usefixtures(...)``) wherever a
    test asserts on what a widget sends.
    """
    real_comm = getattr(widget_module, "Comm", None)
    if real_comm is None:
        return

    class DummyComm(real_comm):  # type: ignore[valid-type,misc]
        kernel = "attached"

        def __init__(self, *args, **kwargs):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                super().__init__(*args, **kwargs)
            self.messages = []

        def open(self, *args, **kwargs):
            pass

        def send(self, *args, **kwargs):
            self.messages.append((args, kwargs))

        def close(self, *args, **kwargs):
            pass

    monkeypatch.setattr(widget_module, "Comm", DummyComm)
