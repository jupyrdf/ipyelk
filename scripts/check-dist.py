"""Check for files in dist archives."""

import sys
import tarfile
import zipfile
from pathlib import Path

import tomllib

HERE = Path(__file__).parent
ROOT = HERE.parent
UTF8 = {"encoding": "utf-8"}

DIST = ROOT / "dist"
PPT = ROOT / "pyproject.toml"
LICENSE = ROOT / "LICENSE.txt"
COPYRIGHT = ROOT / "COPYRIGHT.md"
EPL = ROOT / "third-party/epl-v10.html"
TPL_PATH = (
    "share/jupyter/labextensions/@jupyrdf/jupyter-elk/static/third-party-licenses.json"
)
TPL = ROOT / "src/_d" / TPL_PATH

LICENSE_BYTES = {p: p.read_bytes() for p in [LICENSE, COPYRIGHT, EPL, TPL]}

PY_VERSION = tomllib.loads(PPT.read_text(**UTF8))["project"]["version"]
PFX = f"ipyelk-{PY_VERSION}"

WHEEL_FILES = {
    f"{PFX}.dist-info/LICENSE.txt": LICENSE_BYTES[LICENSE],
    f"{PFX}.data/data/{TPL_PATH}": LICENSE_BYTES[TPL],
}

SDIST_FILES = {
    f"{PFX}/LICENSE.txt": LICENSE_BYTES[LICENSE],
    f"{PFX}/COPYRIGHT.md": LICENSE_BYTES[COPYRIGHT],
    f"{PFX}/third-party/epl-v10.html": LICENSE_BYTES[EPL],
    f"{PFX}/src/_d/{TPL_PATH}": LICENSE_BYTES[TPL],
}


def check_whl(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as whl:
        for fn, fbytes in WHEEL_FILES.items():
            assert whl.read(fn) == fbytes, f"!!! wheel {fn} is wrong"
            print(f"OK wheel {fn}")


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as sdist:
        for fn, fbytes in SDIST_FILES.items():
            assert sdist.extractfile(fn).read() == fbytes, f"!!! sdist {fn} is wrong"
            print(f"OK sdist {fn}")


def main() -> int:
    for path in sorted(DIST.glob("*")):
        if path.name.endswith(".whl"):
            check_whl(path)
        elif path.name.endswith(".tar.gz"):
            check_sdist(path)


if __name__ == "__main__":
    sys.exit(main())
