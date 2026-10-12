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

PROJECT = tomllib.loads(PPT.read_text(**UTF8))["project"]
PY_VERSION = PROJECT["version"]
PFX = f"ipyelk-{PY_VERSION}"
#: the core-metadata license fields (PEP 639) that PyPI shows (#133)
LICENSE_FIELDS = {
    "License-Expression": [PROJECT["license"]],
    "License-File": sorted(PROJECT["license-files"]),
}

WHEEL_FILE_GROUPS = [
    *(
        (
            (f"{PFX}.dist-info/licenses/{p.relative_to(ROOT).as_posix()}",),
            LICENSE_BYTES[p],
        )
        for p in [LICENSE, COPYRIGHT, EPL]
    ),
    ((f"{PFX}.data/data/{TPL_PATH}",), LICENSE_BYTES[TPL]),
]

SDIST_FILES = {
    f"{PFX}/LICENSE.txt": LICENSE_BYTES[LICENSE],
    f"{PFX}/COPYRIGHT.md": LICENSE_BYTES[COPYRIGHT],
    f"{PFX}/third-party/epl-v10.html": LICENSE_BYTES[EPL],
    f"{PFX}/src/_d/{TPL_PATH}": LICENSE_BYTES[TPL],
}


def check_license_fields(where: str, metadata: str) -> None:
    """Fail unless the license fields of ``metadata`` match ``pyproject.toml``."""
    found: dict[str, list[str]] = {}
    for line in metadata.split("\n\n", 1)[0].splitlines():
        key, _, value = line.partition(": ")
        if key in LICENSE_FIELDS:
            found.setdefault(key, []).append(value)
    for key, expected in LICENSE_FIELDS.items():
        assert sorted(found.get(key, [])) == expected, (
            f"!!! {where} {key} is {found.get(key)}, expected {expected}"
        )
        print(f"OK {where} {key}: {', '.join(expected)}")


def check_whl(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as whl:
        names = set(whl.namelist())
        check_license_fields(
            "wheel", whl.read(f"{PFX}.dist-info/METADATA").decode("utf-8")
        )
        for fns, fbytes in WHEEL_FILE_GROUPS:
            for fn in fns:
                if fn in names:
                    assert whl.read(fn) == fbytes, f"!!! wheel {fn} is wrong"
                    print(f"OK wheel {fn}")
                    break
            else:
                raise AssertionError(f"!!! wheel missing one of {', '.join(fns)}")


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as sdist:
        check_license_fields(
            "sdist", sdist.extractfile(f"{PFX}/PKG-INFO").read().decode("utf-8")
        )
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
