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
    the exact pinned dependency, or the two drift apart silently. It must also be
    an exact semver that satisfies the shared ``requiredVersion``: a range there
    (``"^6.2.2"``) is not a version ``ProvideSharedPlugin`` can use, and the
    "Unsatisfied version" warnings return with green tests.
    """
    import json
    import re
    from pathlib import Path

    exact = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")  # no range operators, no prerelease

    def parse(version: str) -> tuple[int, int, int]:
        match = exact.match(version)
        assert match, f"not an exact semver: {version!r}"
        return tuple(int(part) for part in match.groups())  # type: ignore[return-value]

    def satisfies(version: str, required: str) -> bool:
        # only the operators package.json uses today; extend when a new one appears
        if required.startswith("^"):
            low, actual = parse(required[1:]), parse(version)
            # ^ pins the first non-zero component (npm semver caret rule)
            pinned = next((i for i, part in enumerate(low) if part), len(low) - 1)
            return actual[: pinned + 1] == low[: pinned + 1] and actual >= low
        return parse(version) == parse(required)

    package_json = json.loads(
        (Path(__file__).parent.parent / "package.json").read_text(encoding="utf-8")
    )
    dependencies = package_json["dependencies"]
    shared = package_json["jupyterlab"]["sharedPackages"]
    static = {pkg: cfg["version"] for pkg, cfg in shared.items() if "version" in cfg}
    assert static, "at least inversify needs a static shared version"
    for pkg, version in static.items():
        assert dependencies[pkg] == version, (pkg, dependencies[pkg], version)
        assert exact.match(version), (pkg, version)  # what ProvideSharedPlugin needs
        required = shared[pkg].get("requiredVersion", version)
        assert satisfies(version, required), (pkg, version, required)

    # the range check itself, so a wrong helper cannot pass a wrong package.json
    assert satisfies("6.2.2", "^6.1.3")
    assert not satisfies("7.0.0", "^6.1.3")
    assert not satisfies("6.1.2", "^6.1.3")
    assert satisfies("0.12.3", "^0.12.0")
    assert not satisfies("0.13.0", "^0.12.0")
    assert not exact.match("^6.2.2")
