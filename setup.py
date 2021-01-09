# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import re
from pathlib import Path

import setuptools

HERE = Path(__file__).parent

if __name__ == "__main__":
    setuptools.setup(
        version=re.findall(
            r'''__version__ = "([^"]+)"''',
            (HERE / "py_src/ipyelk/_version.py").read_text(encoding="utf-8"),
        )[0],
        data_files = [("", ["third-party/epl-v10.html", "COPYRIGHT.md"])]
    )
