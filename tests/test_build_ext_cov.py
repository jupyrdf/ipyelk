# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""``scripts/build-ext-cov.py`` must leave the normal labextension intact.

``jupyter-builder`` empties ``package.json#jupyterlab.outputDir`` and rewrites its
``package.json`` (``_build.load: "static"``) even when webpack's output is
redirected to the coverage directory, so a full ``pixi run build`` used to end
with an unloadable ``src/_d`` labextension. These tests drive the preservation
helper with stand-ins for the builder (no node, no webpack).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "build-ext-cov.py"


@pytest.fixture
def build_ext_cov():
    spec = importlib.util.spec_from_file_location("build_ext_cov", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clobber_like_the_builder(ext: Path) -> None:
    """What ``jupyter-builder`` does to ``outputDir`` during the coverage build."""
    ext.mkdir(parents=True, exist_ok=True)
    (ext / "package.json").write_text(
        json.dumps({"jupyterlab": {"_build": {"load": "static"}}}), encoding="utf-8"
    )
    (ext / "static").mkdir(exist_ok=True)
    (ext / "static" / "style.js").write_text("", encoding="utf-8")


def failing_build(ext: Path) -> None:
    """A coverage build that clobbers the normal extension, then fails."""
    clobber_like_the_builder(ext)
    raise RuntimeError("webpack failed")


def make_ext(ext: Path) -> dict[str, str]:
    (ext / "static").mkdir(parents=True)
    files = {
        "package.json": json.dumps({
            "jupyterlab": {"_build": {"load": "static/remoteEntry.abc.js"}}
        }),
        "static/remoteEntry.abc.js": "// entry",
        "static/third-party-licenses.json": "{}",
    }
    for name, text in files.items():
        (ext / name).write_text(text, encoding="utf-8")
    return files


def read_ext(ext: Path) -> dict[str, str]:
    return {
        p.relative_to(ext).as_posix(): p.read_text(encoding="utf-8")
        for p in ext.rglob("*")
        if p.is_file()
    }


def test_preserving_restores_the_normal_extension_after_a_clobbering_build(
    build_ext_cov, tmp_path: Path
):
    ext, tmp = tmp_path / "labext", tmp_path / "ext-tmp"
    expected = make_ext(ext)

    with build_ext_cov.preserving(ext, tmp):
        assert not ext.exists()  # nothing for the builder to empty
        clobber_like_the_builder(ext)

    assert read_ext(ext) == expected
    assert not tmp.exists()


def test_preserving_restores_the_normal_extension_when_the_build_fails(
    build_ext_cov, tmp_path: Path
):
    ext, tmp = tmp_path / "labext", tmp_path / "ext-tmp"
    expected = make_ext(ext)

    with (
        pytest.raises(RuntimeError, match="webpack"),
        build_ext_cov.preserving(ext, tmp),
    ):
        failing_build(ext)

    assert read_ext(ext) == expected
    assert not tmp.exists()


def test_preserving_restores_absence_without_a_prior_build(
    build_ext_cov, tmp_path: Path
):
    ext, tmp = tmp_path / "labext", tmp_path / "ext-tmp"

    with build_ext_cov.preserving(ext, tmp):
        clobber_like_the_builder(ext)

    # a first-ever `pixi run build-js-ext-cov` had no extension: the builder's
    # unloadable stub must not be left behind as if it were one
    assert not ext.exists()
    assert not tmp.exists()


def test_preserving_refuses_to_overwrite_a_stale_backup(build_ext_cov, tmp_path: Path):
    """After an interrupted run ``tmp`` may be the only intact copy: never clobber it."""
    ext, tmp = tmp_path / "labext", tmp_path / "ext-tmp"
    expected = make_ext(ext)
    ext.rename(tmp)
    clobber_like_the_builder(ext)
    stub = read_ext(ext)

    with (
        pytest.raises(FileExistsError, match="ext-tmp"),
        build_ext_cov.preserving(ext, tmp),
    ):
        pytest.fail("the block must not run")

    assert read_ext(tmp) == expected
    assert read_ext(ext) == stub  # nothing was mutated


def test_main_moves_the_real_extension_aside(build_ext_cov):
    """The script targets ``package.json#jupyterlab.outputDir``, as the builder does."""
    pkg = json.loads(
        (SCRIPT.parent.parent / "package.json").read_text(encoding="utf-8")
    )
    assert SCRIPT.parent.parent / pkg["jupyterlab"]["outputDir"] == build_ext_cov.EXT
    assert build_ext_cov.EXT_TMP.parent == build_ext_cov.BUILD
