"""Reporting for ipyelk."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import site
import sys
import tempfile
from pathlib import Path
from subprocess import call
from typing import Any

UTF8 = {"encoding": "utf-8"}
HERE = Path(__file__).parent
ROOT = HERE.parent
BUILD = ROOT / "build"
REPORTS = BUILD / "reports"
REPORT_ATEST = REPORTS / "atest"
REPORT_UTEST = REPORTS / "utest"
REPORT_ALLCOV = REPORTS / "htmlcov"

PYPROJECT = f"""
[tool.coverage.paths]
source = [
    "{ROOT}/src",
    "{site.getsitepackages()[0]}",
]

[tool.coverage.html]
skip_empty = true
title = "ALL"
show_contexts = true
directory = "{REPORT_ALLCOV}"

[tool.coverage.report]
show_missing = true
"""


def main() -> int:
    all_py_cov = [
        *sorted(REPORT_ATEST.glob("*/pabot_results/*/pycov/.coverage*")),
        REPORT_UTEST / ".coverage",
    ]

    if not all_py_cov:
        print("No Python coverage found")
        return 1

    with tempfile.TemporaryDirectory() as td:
        kwargs: Any = {"cwd": td}
        tdp = Path(td)
        (tdp / "pyproject.toml").write_text(PYPROJECT, **UTF8)
        call(["coverage", "combine", "--keep", *all_py_cov], **kwargs)
        rc = call(["coverage", "report", "--skip-covered"], **kwargs)
        call(["coverage", "html"], **kwargs)
        for path in REPORT_ALLCOV.rglob("*.html"):
            path.write_text(path.read_text(**UTF8).replace(f"{ROOT}/", ""), **UTF8)

    return rc


if __name__ == "__main__":
    sys.exit(main())
