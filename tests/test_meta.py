# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

try:
    from importlib.metadata import version
except Exception:
    from importlib_metadata import version

from pathlib import Path
from typing import Any


def test_meta() -> None:
    """Verify the version is advertised."""
    import ipyelk

    assert hasattr(ipyelk, "__version__")
    assert ipyelk.__version__ == version("ipyelk")


def test_pixi_versions(
    the_pixi_version: str,
    a_file_with_pixi_versions: Path,
    pixi_versions_in_a_file: set[str],
) -> None:
    """Verify the ``pixi`` version is consistent."""
    assert len(pixi_versions_in_a_file) == 1, a_file_with_pixi_versions
    assert min(pixi_versions_in_a_file) == the_pixi_version, pixi_versions_in_a_file


def test_labextension() -> None:
    """Verify the labextension path metadata is as expected."""
    import ipyelk

    assert len(ipyelk._jupyter_labextension_paths()) == 1


def test_changelog_versions(
    the_changelog_text: str, the_js_version: str, the_py_version: str
) -> None:
    """Verify ``CHANGELOG.md`` contains the current versions."""
    assert f"### `ipyelk {the_py_version}`" in the_changelog_text
    assert f"### `@jupyrdf/jupyter-elk {the_js_version}`" in the_changelog_text


def test_compatible_versions(the_js_version: str, the_py_version: str) -> None:
    """Verify the calculated versions are consistent."""
    from ipyelk.constants import EXTENSION_SPEC_VERSION, __version__

    assert __version__ == the_py_version
    assert the_js_version == EXTENSION_SPEC_VERSION


def test_py_version(the_readme_text: str, the_pyproject_data: dict[str, Any]) -> None:
    """Verify the bottom python pin is accurate."""
    requires_python = the_pyproject_data["project"]["requires-python"]
    assert f"""python {requires_python}""" in the_readme_text


def test_static_shared_package_versions() -> None:
    """Verify statically declared shared-module versions match the dependency pins.

    ``jupyterlab.sharedPackages.<pkg>.version`` is only needed where webpack cannot
    read the version itself (e.g. ``inversify`` resolves to ``lib/esm/index.js``,
    whose sibling ``package.json`` carries no version). Such a static value must be
    an exact version, equal to the pinned dependency, and inside the declared
    ``requiredVersion`` range, or the three drift apart silently.
    """
    import json
    import re

    exact = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
    ranged = re.compile(r"^([\^~]?)(\d+)\.(\d+)\.(\d+)$")

    def parse(version: str) -> tuple[int, int, int]:
        match = exact.match(version)
        assert match, f"{version!r} is not an exact semver (no ^ or ~ allowed)"
        major, minor, patch = match.groups()
        return int(major), int(minor), int(patch)

    def satisfies(version: str, required: str) -> bool:
        match = ranged.match(required)
        assert match, f"unsupported requiredVersion {required!r}"
        op, *floor_parts = match.groups()
        floor = tuple(int(n) for n in floor_parts)
        if not op:
            return parse(version) == floor
        if op == "~" or floor[0] == 0:
            ceiling = (floor[0], floor[1] + 1, 0)
        else:
            ceiling = (floor[0] + 1, 0, 0)
        return floor <= parse(version) < ceiling

    package_json = json.loads(
        (Path(__file__).parent.parent / "package.json").read_text(encoding="utf-8")
    )
    dependencies = package_json["dependencies"]
    shared = package_json["jupyterlab"]["sharedPackages"]
    static = {pkg: cfg for pkg, cfg in shared.items() if "version" in cfg}
    assert static, "at least inversify needs a static shared version"
    for pkg, cfg in static.items():
        version = cfg["version"]
        parse(version)
        assert dependencies[pkg] == version, (pkg, dependencies[pkg], version)
        required = cfg.get("requiredVersion", version)
        assert satisfies(version, required), (pkg, version, required)
