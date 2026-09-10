"""Build instrumented extension."""

import json
import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from subprocess import call

UTF8 = {"encoding": "utf-8"}
HERE = Path(__file__).parent
ROOT = HERE.parent
PKG_JSON = ROOT / "package.json"
PKG_DATA = json.loads(PKG_JSON.read_text(**UTF8))
LIB = ROOT / "lib"

BUILD = ROOT / "build"

LIB_TMP = BUILD / "lib-tmp"
TSBUILDINFO = BUILD / "tsc"
COV_EXT = BUILD / "labextensions-cov"
EXT_PKG_JSON = COV_EXT / PKG_DATA["name"] / PKG_JSON.name
# the normal (uninstrumented) labextension: `jupyter-builder` empties `outputDir` and
# rewrites its package.json (`_build.load: "static"`) even when webpack's output is
# redirected to COV_EXT, so it is moved aside for the duration of the coverage build
EXT = ROOT / PKG_DATA["jupyterlab"]["outputDir"]
EXT_TMP = BUILD / "ext-tmp"


@contextmanager
def preserving(ext: Path, tmp: Path) -> Iterator[None]:
    """Keep ``ext`` exactly as it was (present or absent) across the block.

    A pre-existing ``tmp`` (an interrupted earlier run) may be the only intact
    copy of the extension, so it is never overwritten.
    """
    if tmp.exists():
        msg = f"{tmp} exists: restore or remove it before rebuilding"
        raise FileExistsError(msg)
    had_ext = ext.exists()
    if had_ext:
        print("... moving", ext, "aside to", tmp)
        ext.rename(tmp)
    try:
        yield
    finally:
        shutil.rmtree(ext, ignore_errors=True)  # the builder's stub, if any
        if had_ext:
            print("... restoring", ext)
            tmp.rename(ext)


def main() -> int:
    """Work around webpack limitations to get an out-of-tree build with coverage."""
    BUILD.mkdir(exist_ok=True, parents=True)

    if not EXT_PKG_JSON.exists():
        print("... cleaning", TSBUILDINFO)
        [p.unlink() for p in TSBUILDINFO.glob("*.cov")]

    if LIB.exists():
        print("... backing up", LIB, "to", LIB_TMP)
        shutil.rmtree(LIB_TMP, ignore_errors=True)
        shutil.copytree(LIB, LIB_TMP)

    try:
        with preserving(EXT, EXT_TMP):
            return build_cov()
    finally:
        shutil.rmtree(LIB, ignore_errors=True)
        if LIB_TMP.exists():
            print("... restoring lib")
            LIB_TMP.rename(LIB)


def build_cov() -> int:
    """Build the instrumented ``lib`` and labextension into ``COV_EXT``."""
    shutil.rmtree(COV_EXT, ignore_errors=True)

    print("... building instrumented lib")
    rc = call(["jlpm", "build:ts:cov"])
    if rc:
        return rc

    env = dict(os.environ)
    env["WITH_TOTAL_COVERAGE"] = "1"

    print("... building", COV_EXT)
    rc = call(["jlpm", "build:ext"], env=env)
    if rc:
        return rc

    print("... patching", EXT_PKG_JSON)
    remote = min(COV_EXT.rglob("remoteEntry.*.js"))
    print("... found remote", remote)
    PKG_DATA["jupyterlab"]["_build"] = {
        "load": f"static/{remote.name}",
        "extension": "./extension",
    }
    EXT_PKG_JSON.write_text(json.dumps(PKG_DATA, indent=2), **UTF8)

    return 0


if __name__ == "__main__":
    sys.exit(main())
