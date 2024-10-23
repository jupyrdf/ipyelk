"""Build instrumented extension."""

import json
import os
import shutil
import sys
from pathlib import Path
from subprocess import call

UTF8 = {"encoding": "utf-8"}
HERE = Path(__file__).parent
ROOT = HERE.parent
PKG_JSON = ROOT / "package.json"
PKG_DATA = json.loads(PKG_JSON.read_text(**UTF8))
LIB = ROOT / "lib"

BUILD = ROOT / "build"

COV_BUILDINFO = BUILD / ".src.cov.tsbuildinfo"
LIB_TMP = BUILD / "lib-tmp"
COV_EXT = BUILD / "labextensions-cov"
EXT_PKG_JSON = COV_EXT / PKG_DATA["name"] / PKG_JSON.name


def main() -> int:
    """Work around webpack limitations to get an out-of-tree build with coverage."""
    COV_BUILDINFO.unlink(missing_ok=True)

    BUILD.mkdir(exist_ok=True, parents=True)

    if LIB.exists():
        print("... copying", LIB, "to", LIB_TMP)
        shutil.rmtree(LIB_TMP, ignore_errors=True)
        LIB.rename(LIB_TMP)

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

    if LIB_TMP.exists():
        print("... restoring lib")
        shutil.rmtree(LIB, ignore_errors=True)
        LIB_TMP.rename(LIB)

    return 0


if __name__ == "__main__":
    sys.exit(main())
