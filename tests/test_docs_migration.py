# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Keep ``docs/migration.md`` true to the code and to the CHANGELOG.

A section of the guide that starts with the note "This change is in [#N], which is
not merged yet" is *pending*: its pull request is not on this branch. When the pull
request merges, these tests fail until its notes are deleted.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import importlib
import inspect
import io
import logging
import pkgutil
import re
import warnings
from operator import itemgetter
from pathlib import Path

import pytest

import ipyelk
from ipyelk.exceptions import DeprecatedImportError, RegistrationMethod, RemovedAPI

ROOT = Path(__file__).parent.parent
MIGRATION_MD = ROOT / "docs/migration.md"
CHANGELOG_MD = ROOT / "CHANGELOG.md"
UTF8 = {"encoding": "utf-8"}

PENDING = "which is not merged yet"
PENDING_NOTE = re.compile(r"This change is in \[#(\d+)\], " + PENDING)

#: API names of the 3.0.0 breaking changes that the guide need not name: the
#: machinery behind the errors, a type in an annotation, an example's old comment
NOT_IN_GUIDE = {
    "Callable",
    "RegistrationMethod",
    "ipyelk.exceptions.RemovedAPI",
    "toolbar.commands",
}


def _guide() -> str:
    return MIGRATION_MD.read_text(**UTF8)


# the CHANGELOG ##########################################################################


def _breaking_entries() -> list[str]:
    """The top-level entries under ``3.0.0`` > ``ipyelk`` > ``Breaking changes``."""
    release = CHANGELOG_MD.read_text(**UTF8).split("\n## ")[1]
    assert release.startswith("`3.0.0"), "the first release is no longer 3.0.0"
    section = release.split("\n#### Breaking changes\n", 1)[1]
    section = re.split(r"\n#{2,4} ", section, maxsplit=1)[0]  # to the next heading
    entries = re.split(r"\n(?=- )", section.strip())
    assert all(entry.startswith("- ") for entry in entries), entries[0][:80]
    return entries


def _api_names(text: str) -> set[str]:
    """The dotted or capitalized names in code spans, without call arguments."""
    names = set()
    for span in re.findall(r"`([^`]+)`", text):
        name = re.sub(r"\(.*\)$", "", span)
        if re.fullmatch(r"[A-Za-z_][\w.]*", name) and (
            "." in name or name[0].isupper()
        ):
            names.add(name)
    return names


@pytest.mark.parametrize(
    "entry", _breaking_entries(), ids=lambda entry: entry[2:40].replace(" ", "_")
)
def test_migration_covers_breaking_change(entry: str) -> None:
    """Every name that a breaking change mentions is on the guide."""
    guide = _guide()
    missing = sorted(n for n in _api_names(entry) - NOT_IN_GUIDE if n not in guide)
    assert not missing, f"docs/migration.md does not mention {missing}:\n{entry}"


# the table of removed names #############################################################


def _modules() -> list[str]:
    walked = pkgutil.walk_packages(ipyelk.__path__, "ipyelk.")
    return ["ipyelk", *sorted(info.name for info in walked)]


def _removed_in_code() -> tuple[set[str], dict[str, list[type]]]:
    """The removed names that the code defines, and every class by its name."""
    removed: set[str] = set()
    classes: dict[str, list[type]] = {}
    for name in _modules():
        try:
            module = importlib.import_module(name)
        except DeprecatedImportError:
            removed.add(name)
            continue
        removed |= {f"{name}.{key}" for key in getattr(module, "_REMOVED", {})}
        for value in vars(module).values():
            if isinstance(value, type) and value.__module__ == name:
                classes.setdefault(value.__name__, []).append(value)
                removed |= {
                    f"{value.__name__}.{attr}"
                    for attr, member in vars(value).items()
                    if isinstance(member, (RemovedAPI, RegistrationMethod))
                }
    return removed, classes


def _table() -> dict[str, bool]:
    """The names in the table of removed names, each with ``True`` if pending."""
    guide = _guide().split("(migration-removed-names)=\n\n## ", 1)[1]
    section = guide.split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")][2:]
    assert rows, "the table of removed names is gone"
    names = {}
    for row in rows:
        cell = row.split("|")[1]
        for span in re.findall(r"`([^`]+)`", cell):
            if re.fullmatch(r"[\w.]+", span):
                names[span] = PENDING in cell
    return names


def test_migration_table_lists_every_removed_name() -> None:
    """The table lists every name for which ``ipyelk`` raises a removed-name error."""
    removed, _ = _removed_in_code()
    missing = sorted(removed - set(_table()))
    assert not missing, f"add rows for {missing} to the table of removed names"


def test_migration_table_lists_only_removed_names() -> None:
    """Each name in the table raises its error, unless its row is pending."""
    removed, classes = _removed_in_code()

    def is_removed(name: str) -> bool:
        owner, _, attr = name.rpartition(".")
        inherited = any(
            isinstance(
                inspect.getattr_static(cls, attr, None),
                (RemovedAPI, RegistrationMethod),
            )
            for cls in classes.get(owner, [])
        )
        return name in removed or inherited

    table = _table()
    merged = sorted(n for n, pending in table.items() if pending and is_removed(n))
    stale = sorted(
        n for n, pending in table.items() if not pending and not is_removed(n)
    )
    assert not merged, f"delete '{PENDING}' from the rows of {merged}: they merged"
    assert not stale, f"the code does not remove {stale}: fix their rows"


# the examples ###########################################################################


def _blocks() -> list[dict]:
    """The ``2.x`` and ``3.0`` Python blocks, with their setup and expected text.

    A ``# both versions`` block is the setup of every block under its heading,
    including the blocks of deeper headings.
    """
    blocks: list[dict] = []
    scopes: list[tuple[int, list[str]]] = []
    section, pr = "", None
    lines = _guide().splitlines()
    i = 0
    while i < len(lines):
        heading = re.match(r"^(#{2,4}) (.*)", lines[i])
        if heading:
            level = len(heading.group(1))
            scopes = [scope for scope in scopes if scope[0] < level] + [(level, [])]
            section, pr = heading.group(2), None
        note = PENDING_NOTE.search(lines[i])
        if note:
            pr = note.group(1)
        fence = re.match(r"^```(\w+)\s*$", lines[i])
        if fence:
            end = lines.index("```", i + 1)
            body = "\n".join(lines[i + 1 : end])
            label = re.match(r"(# (2\.x|3\.0))?", body)[2]
            if fence.group(1) == "python" and body.startswith("# both versions"):
                scopes[-1][1].append(body)
            elif fence.group(1) == "python":
                setup = [block for _, scope in scopes for block in scope]
                blocks.append({
                    "id": f"L{i + 1}-{label}",
                    "section": section,
                    "label": label,
                    "pr": pr,
                    "src": "\n".join([*setup, body]),
                    "expect": None,
                })
            elif fence.group(1) == "text" and blocks and blocks[-1]["label"] == "2.x":
                blocks[-1]["expect"] = blocks[-1]["expect"] or body
            i = end
        i += 1
    return blocks


class _ShowError(logging.Handler):
    """Print what a notebook shows for an error in a widget callback."""

    def emit(self, record: logging.LogRecord) -> None:
        error = record.exc_info and record.exc_info[1]
        if error:  # the class name without its module, as IPython shows it
            print(f"{type(error).__name__}: {error}")


def _run(src: str) -> tuple[list[str], bool]:
    """Run a block like a notebook cell: the lines that it prints, shows or raises,
    and if it raised.
    """

    async def cell() -> None:
        code = compile(src, "<block>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        result = eval(code, {"__name__": "__main__"})  # ruff: ignore[suspicious-eval-usage]
        if inspect.iscoroutine(result):
            await result
        await asyncio.sleep(0.05)  # let the scheduled runs finish

    out = io.StringIO()
    handler = _ShowError()
    raised = False
    logger = logging.getLogger("traitlets")
    logger.addHandler(handler)
    try:
        with (
            contextlib.redirect_stdout(out),
            warnings.catch_warnings(record=True) as shown,
        ):
            # what IPython shows: a DeprecationWarning only from the notebook's code
            warnings.simplefilter("always")
            warnings.simplefilter("ignore", DeprecationWarning)
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            warnings.filterwarnings(
                "always", category=DeprecationWarning, module="__main__"
            )
            try:
                asyncio.run(cell())
            except Exception as error:
                raised = True
                print(f"{type(error).__name__}: {error}")
    finally:
        logger.removeHandler(handler)
    shown_text = [f"{w.category.__name__}: {w.message}" for w in shown]
    return [*shown_text, *out.getvalue().splitlines()], raised


def _norm(lines: list[str]) -> str:
    return "\n".join(" ".join(line.split()) for line in lines if line.strip())


@pytest.mark.parametrize("block", _blocks(), ids=itemgetter("id"))
def test_migration_example(block: dict) -> None:
    """A 2.x block shows its quoted text, and a 3.0 block runs and shows no error,
    unless pending.
    """
    assert block["label"], "start the block with # 2.x, # 3.0 or # both versions"
    if block["pr"] and block["label"] != "2.x":
        pytest.skip(f"the code of #{block['pr']} is not on this branch")
    lines, raised = _run(block["src"])
    got, expect = _norm(lines), _norm((block["expect"] or "").splitlines())
    if not raised:  # a printed value or a warning: whole lines, not a part of a line
        got, expect = f"\n{got}\n", f"\n{expect}\n" if expect else ""
    if block["label"] == "3.0":
        assert not raised, f"{block['section']}: the 3.0 code fails: {got}"
        shown = re.search(r"\w+(Error|Warning):", got)
        assert not shown, f"{block['section']}: the 3.0 code shows an error: {got}"
    elif block["pr"]:
        assert not expect or expect not in got, (
            f"{block['section']}: the 2.x code shows the 3.0 text, so #{block['pr']}"
            " merged: delete its notes"
        )
    else:
        assert expect in got, f"{block['section']}: expected {expect!r}, got {got!r}"
