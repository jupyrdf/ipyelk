# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import os
import re
import warnings
from pathlib import Path

import setuptools

READTHEDOCS = os.environ.get("READTHEDOCS", None) == "True"

HERE = Path(__file__).parent
EXT = HERE / "py_src" / "ipyelk" / "labextension"
EXT_NAME = "@jupyrdf/jupyter-elk"

EXT_FILES = {}
SHARE = f"share/jupyter/labextensions/{EXT_NAME}"

for ext_path in [EXT] + [d for d in EXT.rglob("*") if d.is_dir()]:
    if ext_path == EXT:
        target = str(SHARE)
    else:
        target = f"{SHARE}/{ext_path.relative_to(EXT)}"
    EXT_FILES[target] = [
        str(p.relative_to(HERE).as_posix())
        for p in ext_path.glob("*")
        if not p.is_dir()
    ]

ALL_FILES = sum(EXT_FILES.values(), [])

remote_entries = []
pat = re.compile("remoteEntry.*.js$")
for file in ALL_FILES:
    if re.search(pat, file):
        remote_entries.append(file)
num_remotes = len(remote_entries)
if not READTHEDOCS and num_remotes != 1:
    warnings.warn(f"expect _exactly one_ remoteEntry.*.js$ found {num_remotes}")

EXT_FILES[str(SHARE)] += ["install.json"]


if __name__ == "__main__":
    setuptools.setup(
        version=re.findall(
            r'''__version__ = "([^"]+)"''',
            (HERE / "py_src/ipyelk/_version.py").read_text(encoding="utf-8"),
        )[0],
        data_files=[
            ("", ["third-party/epl-v10.html", "COPYRIGHT.md"]),
            *[(k, v) for k, v in EXT_FILES.items()],
        ],
    )
