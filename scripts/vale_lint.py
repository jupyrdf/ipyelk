# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Lint source prose with Vale; fail on any warning or error.

Vale itself only exits non-zero on errors, so this reads its JSON output.
Notebook markdown is linted from ``build/nblint``: run
``python scripts/nblint.py --extract-only examples`` first.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PATHS = [
    *sorted(p.name for p in ROOT.glob("*.md")),
    "docs",
    "src",
    "build/nblint",
]
GLOB = "--glob=*.{md,py}"
CANARY = "This sentense is a canary.\n"
CANARY_CHECK = "IPyElk.Spelling"
UTF8 = {"encoding": "utf-8"}


def dicpath() -> str:
    """Find the conda-forge hunspell dictionaries."""
    prefix = Path(os.environ.get("CONDA_PREFIX", sys.prefix))
    candidates = [prefix / "share", prefix / "Library/share"]
    for share in candidates:
        path = share / "hunspell_dictionaries"
        if (path / "en_US.dic").exists():
            return str(path)
    msg = f"no en_US.dic under {candidates}"
    raise FileNotFoundError(msg)


def vale(*args: str, stdin: str | None = None) -> dict[str, list[dict]]:
    """Run vale, returning alerts keyed by path."""
    env = dict(os.environ, DICPATH=dicpath())
    proc = subprocess.run(
        ["vale", "--no-exit", "--output=JSON", *args],
        cwd=ROOT,
        env=env,
        input=stdin,
        capture_output=True,
        check=False,
        **UTF8,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise


def summarize(alerts: dict[str, list[dict]]) -> list[str]:
    """Format one line per alert."""
    return [
        f"{path}:{a['Line']}:{a['Span'][0]}: {a['Severity']} [{a['Check']}] "
        f"{a['Message']}"
        for path, file_alerts in sorted(alerts.items())
        for a in file_alerts
    ]


def main() -> int:
    """Lint and report; return 1 on any alert."""
    canary = vale("--ext=.md", stdin=CANARY)
    if not any(a["Check"] == CANARY_CHECK for a in canary.get("stdin.md", [])):
        print(f"!!! canary not caught by {CANARY_CHECK}: {canary}", file=sys.stderr)
        return 1

    lines = summarize(vale(GLOB, *PATHS))
    if lines:
        print(*lines, sep="\n")
    print(f"vale: {len(lines)} warning(s) or error(s)")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary and lines:
        with Path(step_summary).open("a", **UTF8) as fh:
            fh.write("### vale\n\n```\n" + "\n".join(lines) + "\n```\n")

    return min(len(lines), 1)


if __name__ == "__main__":
    sys.exit(main())
