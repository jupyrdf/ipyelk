# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Fail on a work marker in code that does not name the issue that tracks it.

Write a marker as ``TODO(#123): what to do``, with ``FIXME``, ``XXX`` or ``HACK``
in place of ``TODO`` as needed. Every marker then points to a GitHub issue, and
``git grep "TODO(#"`` lists them. Markdown files are prose, so they are not checked.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).parent.parent
#: a marker word that is not followed by ``(#<issue number>)``
UNTRACKED = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b(?!\(#\d+\))")
SUFFIXES = {
    ".cfg",
    ".cjs",
    ".css",
    ".html",
    ".ini",
    ".ipynb",
    ".js",
    ".mjs",
    ".py",
    ".robot",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
#: this file names the marker words in its pattern
SKIP = {"scripts/check_todos.py"}


def untracked(text: str) -> Iterator[tuple[int, str]]:
    """Yield the line number and text of each line with a marker that names no issue."""
    for number, line in enumerate(text.splitlines(), start=1):
        if UNTRACKED.search(line):
            yield number, line.strip()


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [path for path in out.splitlines() if Path(path).suffix in SUFFIXES]


def main() -> int:
    found = 0
    for path in tracked_files():
        if path in SKIP or not (ROOT / path).exists():
            continue
        text = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        for number, line in untracked(text):
            print(f"{path}:{number}: {line}")
            found += 1
    if found:
        print(f"{found} marker(s) without an issue: write them as TODO(#123): ...")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
