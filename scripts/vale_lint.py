# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Lint source prose with Vale; fail on any warning or error.

Vale itself only exits non-zero on errors, so this reads its JSON output.
Exits 0 when clean, 1 on findings, 2 when Vale (or its input) is broken.
Notebook markdown is linted from ``build/nblint``: run
``python scripts/nblint.py --extract-only examples`` first.

Vale skips a module docstring that follows a ``#`` comment (the license
header), so module docstrings are also copied, line numbers intact, to
``build/vale_docstrings`` and reported against their source file.
"""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
VALE = ["vale"]
PATHS = [
    *sorted(p.name for p in ROOT.glob("*.md")),
    "build/nblint",
    "docs",
    "scripts",
    "src",
    "tests",
]
DOCSTRINGS = "build/vale_docstrings"
SUFFIXES = (".md", ".py")
GLOB = "--glob=*.{md,py}"
CANARY_CHECK = "IPyElk.Spelling"
ALERT_KEYS = {"Check", "Line", "Message", "Severity", "Span"}
UTF8 = {"encoding": "utf-8"}


class ValeError(RuntimeError):
    """Vale crashed, or its output can't be trusted."""


def module_docstring(source: str) -> str | None:
    """Return only the module docstring, on its original lines, or ``None``."""
    body = ast.parse(source).body
    node = body[0] if body else None
    if not (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        return None
    lines = source.splitlines()[node.lineno - 1 : node.end_lineno]
    return "\n" * (node.lineno - 1) + "\n".join(lines) + "\n"


CANARIES = [
    (".md", "This sentense is a canary.\n"),
    (".py", '"""This sentense is a canary."""\n'),
    (".py", module_docstring('# header\n"""This sentense is a canary."""\n')),
]


def dicpath() -> str | None:
    """Find the conda-forge hunspell dictionaries, if installed."""
    prefix = Path(os.environ.get("CONDA_PREFIX", sys.prefix))
    for share in [prefix / "share", prefix / "Library/share"]:
        path = share / "hunspell_dictionaries"
        if (path / "en_US.dic").exists():
            return str(path)
    return None


def check_paths(root: Path, paths: list[str]) -> None:
    """Fail on a path that is missing or has nothing to lint."""
    for rel in paths:
        path = root / rel
        if path.is_file():
            continue
        if not path.is_dir():
            msg = f"missing: {rel}"
            raise ValeError(msg)
        if not any(p.suffix in SUFFIXES for p in path.rglob("*")):
            msg = f"no {SUFFIXES} files in: {rel}"
            raise ValeError(msg)


def write_docstrings(root: Path, paths: list[str]) -> list[str]:
    """Copy module docstrings for linting; return their folder, if any."""
    out = root / DOCSTRINGS
    shutil.rmtree(out, ignore_errors=True)
    for rel in paths:
        for py in sorted((root / rel).rglob("*.py")):
            try:
                stub = module_docstring(py.read_text(**UTF8))
            except (SyntaxError, UnicodeDecodeError) as err:
                msg = (
                    f"can't read the module docstring of {py.relative_to(root)}: {err}"
                )
                raise ValeError(msg) from err
            if stub:
                dest = out / py.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(stub, **UTF8)
    return [DOCSTRINGS] if out.exists() else []


def parse(stdout: str) -> dict[str, list[dict]]:
    """Parse ``{path: [alert, ...]}``, or raise."""
    try:
        alerts = json.loads(stdout)
    except json.JSONDecodeError as err:
        msg = f"not JSON: {err}"
        raise ValeError(msg) from err
    if not isinstance(alerts, dict) or not all(
        isinstance(path, str)
        and isinstance(file_alerts, list)
        and all(isinstance(a, dict) and a.keys() >= ALERT_KEYS for a in file_alerts)
        for path, file_alerts in alerts.items()
    ):
        msg = f"not {{path: [alert, ...]}}: {stdout[:500]}"
        raise ValeError(msg)
    return alerts


def vale(*args: str, stdin: str | None = None) -> dict[str, list[dict]]:
    """Run vale, returning alerts keyed by path."""
    env = dict(os.environ)
    found = dicpath()
    if found:
        env["DICPATH"] = found
    proc = subprocess.run(
        [*VALE, "--no-exit", "--output=JSON", *args],
        cwd=ROOT,
        env=env,
        input=stdin,
        capture_output=True,
        check=False,
        **UTF8,
    )
    if proc.returncode:
        msg = f"vale exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
        raise ValeError(msg)
    if not proc.stdout.strip():
        msg = f"vale wrote no output:\n{proc.stderr}"
        raise ValeError(msg)
    return parse(proc.stdout)


def summarize(alerts: dict[str, list[dict]]) -> list[str]:
    """Format one line per alert, mapping docstring copies to their source."""
    prefix = f"{DOCSTRINGS}/"
    found = {
        (
            path.replace("\\", "/").removeprefix(prefix),
            a["Line"],
            a["Span"][0],
            f"{a['Severity']} [{a['Check']}] {a['Message']}",
        )
        for path, file_alerts in alerts.items()
        for a in file_alerts
    }
    return [f"{p}:{line}:{col}: {msg}" for p, line, col, msg in sorted(found)]


def lint() -> list[str]:
    """Check the canaries, then lint every path."""
    for ext, text in CANARIES:
        caught = vale(f"--ext={ext}", stdin=text).get(f"stdin{ext}", [])
        if not any(a["Check"] == CANARY_CHECK for a in caught):
            msg = f"{CANARY_CHECK} missed the {ext} canary: {text!r}"
            raise ValeError(msg)
    check_paths(ROOT, PATHS)
    docstrings = write_docstrings(ROOT, [p for p in PATHS if (ROOT / p).is_dir()])
    return summarize(vale(GLOB, *PATHS, *docstrings))


def main() -> int:
    """Lint and report."""
    try:
        lines = lint()
    except ValeError as err:
        print(f"!!! {err}", file=sys.stderr)
        return 2

    if lines:
        print(*lines, sep="\n")
    print(f"vale: {len(lines)} warning(s) or error(s)")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary and lines:
        with Path(step_summary).open("a", **UTF8) as fh:
            fh.write("### vale\n\n```\n" + "\n".join(lines) + "\n```\n")

    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
