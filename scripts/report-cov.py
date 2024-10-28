"""Reporting for ipyelk."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import json
import math
import os
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path
from subprocess import PIPE, Popen, call, check_output
from typing import Any

UTF8: Any = {"encoding": "utf-8"}
HERE = Path(__file__).parent
ROOT = HERE.parent
SRC = ROOT / "src"
BUILD = ROOT / "build"
REPORTS = BUILD / "reports"
PRETTIER = ["jlpm", "prettier", "--write"]

STEP_SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")

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

WIN = platform.system() == "Windows"

if WIN:
    print("Not checking windows coverage...")
    FAIL_UNDER = "0"

PYPROJECT = f"""
[tool.coverage.html]
skip_empty = true
title = "ALL"
show_contexts = true
directory = '{REPORT_PY_ALLCOV}'

[tool.coverage.report]
show_missing = true
"""


def norm_nums(raw: str, skip_cols: list[int] | None = None) -> str:
    """Remove silly precision."""
    skip_cols = skip_cols or []
    cols = raw.split("|")
    new_cols: list[str] = []
    for i, col in enumerate(cols):
        if i in skip_cols:
            new_cols += [col]
        else:
            try:
                new_cols += [f"{math.floor(json.loads(col.strip()))}"]
            except:
                new_cols += [col]
    return " | ".join(new_cols)


def nyc_md(raw: str) -> list[str]:
    """Transform raw `nyc` output into markdown."""
    lines: list[str] = []
    header: list[str] = []
    summary: str | None = None

    in_table = False
    current_path = ""

    for line in raw.splitlines():
        if line.startswith("File"):
            in_table = True
            header += [f"| {line} |"]
        elif not in_table:
            continue
        elif line.startswith("-"):
            if len(header) > 1:
                break
            first, rest = line.split("|", 1)
            rest = rest.replace("-|", ":|")
            header += [f"| {first} | {rest} "]
        elif line.startswith("All files"):
            first_col, rest = line.split("|", 1)
            rest_cols = norm_nums(rest).split("|")
            line = " | ".join([
                f"**{c.strip()}**" if c.strip() else c for c in [first_col, *rest_cols]
            ])
            summary = f"| {line} |"
        elif "|" in line:
            first_col, rest = line.split("|", 1)
            first_col = first_col.strip()
            if not first_col.endswith((".ts", ".tsx")):
                current_path = first_col
                continue
            lines += [f"| {current_path}/{first_col} |{norm_nums(rest, [4])} |"]
        else:
            break

    if header and lines and summary:
        return ["## js coverage", "", *header, *lines, summary, ""]
    print("!!! Failed to gather js coverage...")

    return []


def js_cov(summary_lines: list[str]) -> int:
    """Gather coverage from all JS sources."""
    all_js_cov = sorted(REPORT_ATEST.rglob("*/jscov/*.json"))

    if not all_js_cov:
        print("No JS coverage from atest")
        return 0 if WIN else 1

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

        proc = Popen(
            [
                *report_args,
                f"--report-dir={REPORT_JS_ALLCOV}",
                "--check-coverage",
                "--skip-full",
            ],
            stdout=PIPE,
            **UTF8,
        )
        rc = proc.wait()

        if STEP_SUMMARY and proc.stdout:
            summary_lines += nyc_md(proc.stdout.read())

    return rc


def py_cov(summary_lines: list[str]) -> int:
    """Gather coverage from all python sources."""
    all_py_cov = [
        *sorted(REPORT_ATEST.glob("*/pabot_results/*/pycov/.coverage*")),
        REPORT_UTEST / ".coverage",
    ]

    if not all_py_cov:
        print("No Python coverage found")
        return 0 if WIN else 1

    with tempfile.TemporaryDirectory() as td:
        kwargs: Any = {"cwd": td, **UTF8}
        tdp = Path(td)
        report_args = ["coverage", "report", "--skip-covered"]
        (tdp / "pyproject.toml").write_text(PYPROJECT, **UTF8)
        call(["coverage", "combine", "--keep", *all_py_cov], **kwargs)
        rc = call([*report_args, f"--fail-under={FAIL_UNDER}"], **kwargs)
        if STEP_SUMMARY:
            summary_lines += ["## python coverage", ""]
            try:
                summary_lines += (
                    check_output([*report_args, "--format=markdown"], **kwargs)
                    .strip()
                    .splitlines()
                )
            except Exception as err:
                summary_lines += [
                    f"> there was an error generating coverage summary: `{err}`"
                ]
        call(["coverage", "html"], **kwargs)
        for path in REPORT_PY_ALLCOV.rglob("*.html"):
            path.write_text(path.read_text(**UTF8).replace(f"{ROOT}/", ""), **UTF8)

    return rc


def main() -> int:
    summary_lines: list[str] = []
    rc = max([py_cov(summary_lines), js_cov(summary_lines)])
    if not rc and STEP_SUMMARY:
        raw = "\n".join(summary_lines)
        raw = raw.replace(f"{ROOT}/", "")
        Path(STEP_SUMMARY).write_text(raw, **UTF8)
        # call([*PRETTIER, str(STEP_SUMMARY)])
    return rc


if __name__ == "__main__":
    sys.exit(main())
