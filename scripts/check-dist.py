"""Check for files in dist archives."""

from pathlib import Path
import sys
import zipfile
import tarfile
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
    "src/_d/share/jupyter/labextensions/@jupyrdf/jupyter-elk/static/"
    "third-party-licenses.json"
)
TPL = ROOT / TPL_PATH

LICENSE_BYTES = {p: p.read_bytes() for p in [LICENSE, COPYRIGHT, EPL, TPL]}

PY_VERSION = tomllib.loads(PPT.read_text(**UTF8))["project"]["version"]

WHEEL_FILES = {
    f"ipyelk-{PY_VERSION}.dist-info/LICENSE.txt": LICENSE_BYTES[LICENSE]
}
SDIST_FILES = {
    f"ipyelk-{PY_VERSION}/LICENSE.txt": LICENSE_BYTES[LICENSE],
    f"ipyelk-{PY_VERSION}/COPYRIGHT.md": LICENSE_BYTES[COPYRIGHT],
    f"ipyelk-{PY_VERSION}/third-party/epl-v10.html": LICENSE_BYTES[EPL],
    f"ipyelk-{PY_VERSION}/{TPL_PATH}": LICENSE_BYTES[TPL],
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
