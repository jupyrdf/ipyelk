"""Reporting for ipyelk."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import os
import platform
import re
import shutil
import site
import sys
import tempfile
from pathlib import Path
from subprocess import call
from typing import Any

UTF8 = {"encoding": "utf-8"}
HERE = Path(__file__).parent
ROOT = HERE.parent
SRC = ROOT / "src"
BUILD = ROOT / "build"
REPORTS = BUILD / "reports"

REPORT_ATEST = REPORTS / "atest"
REPORT_UTEST = REPORTS / "utest"
REPORT_PY_ALLCOV = REPORTS / "htmlcov"
REPORT_JS_ALLCOV = REPORTS / "nyc"

CI_YML = ROOT / ".github/workflows/ci.yml"
COV_ENV_VAR = "ALL_PY_COV_FAIL_UNDER"
FAIL_UNDER = (
    os.environ.get(COV_ENV_VAR, "")
    or re.findall(rf"{COV_ENV_VAR}: (\d+)", CI_YML.read_text(**UTF8))[0]
)

if platform.system() == "Windows":
    print("Not checking windows coverage...")
    FAIL_UNDER = "0"

PYPROJECT = f"""
[tool.coverage.paths]
source = [
    '{SRC}',
    '{site.getsitepackages()[0]}',
]

[tool.coverage.html]
skip_empty = true
title = "ALL"
show_contexts = true
directory = '{REPORT_PY_ALLCOV}'

[tool.coverage.report]
show_missing = true
"""


def js_cov() -> int:
    """Gather coverage from all JS sources."""
    all_js_cov = sorted(REPORT_ATEST.rglob("*/jscov/*.json"))

    if not all_js_cov:
        print("No JS coverage from atest")
        return 1

    with tempfile.TemporaryDirectory() as td:
        for js_cov in all_js_cov:
            shutil.copy2(js_cov, Path(td) / js_cov.name)

        report_args = [
            "jlpm",
            "run",
            "nyc",
            "report",
            f"--temp-dir={td}",
        ]

        return call([
            *report_args,
            f"--report-dir={REPORT_JS_ALLCOV}",
            "--check-coverage",
        ])


def py_cov() -> int:
    """Gather coverage from all python sources."""
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
        rc = call(
            [
                "coverage",
                "report",
                "--skip-covered",
                f"--fail-under={FAIL_UNDER}",
            ],
            **kwargs,
        )
        call(["coverage", "html"], **kwargs)
        for path in REPORT_PY_ALLCOV.rglob("*.html"):
            path.write_text(path.read_text(**UTF8).replace(f"{ROOT}/", ""), **UTF8)

    return rc


def main() -> int:
    return max([py_cov(), js_cov()])


if __name__ == "__main__":
    sys.exit(main())
