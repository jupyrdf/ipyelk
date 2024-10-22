# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

try:
    from importlib.metadata import version
except Exception:
    from importlib_metadata import version

from pathlib import Path


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
