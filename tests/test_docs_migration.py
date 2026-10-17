# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Keep ``docs/migration.md`` true to the code and to the CHANGELOG."""

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


def _breaking_entries(changelog: str | None = None) -> list[str]:
    """The top-level entries under ``Breaking changes`` in the ``ipyelk`` section of
    every ``3.0.0`` release. A release without ``Breaking changes`` adds none.
    """
    changelog = CHANGELOG_MD.read_text(**UTF8) if changelog is None else changelog
    releases = [r for r in changelog.split("\n## ")[1:] if r.startswith("`3.0.0")]
    assert releases, "the CHANGELOG has no 3.0.0 release"
    entries: list[str] = []
    for release in releases:
        for package in release.split("\n### ")[1:]:
            if not package.startswith("`ipyelk "):
                continue
            for group in package.split("\n#### ")[1:]:
                title, _, body = group.partition("\n")
                if title == "Breaking changes":
                    entries += re.split(r"\n(?=- )", body.strip())
    assert entries, "no 3.0.0 release has breaking changes"
    assert all(entry.startswith("- ") for entry in entries), entries[0][:80]
    return entries


def test_breaking_entries_of_every_3_0_release() -> None:
    """A new 3.0.0 release on top keeps the breaking changes of the older ones."""
    changelog = CHANGELOG_MD.read_text(**UTF8)
    entries = _breaking_entries(changelog)
    title, older = changelog.split("\n## ", 1)
    newer = "## `3.0.0a99`\n\n### `ipyelk 3.0.0a99`\n\n#### Fixed\n\n- A fix\n\n"
    fixed_only = f"{title}\n{newer}## {older}"
    assert _breaking_entries(fixed_only) == entries
    breaking = fixed_only.replace(
        "#### Fixed", "#### Breaking changes\n\n- `A.b`\n\n#### Fixed", 1
    )
    assert _breaking_entries(breaking) == ["- `A.b`", *entries]


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


def _table(label: str = "migration-removed-names") -> set[str]:
    """The names in the table of removed names, or of the section ``label``."""
    guide = _guide().split(f"({label})=\n\n## ", 1)[1]
    section = guide.split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")][2:]
    assert rows, f"the table of {label} is gone"
    cells = [row.split("|")[1] for row in rows]
    spans = [span for cell in cells for span in re.findall(r"`([^`]+)`", cell)]
    return {span for span in spans if re.fullmatch(r"[\w.]+", span)}


def test_migration_table_lists_every_removed_name() -> None:
    """The table lists every name for which ``ipyelk`` raises a removed-name error."""
    removed, _ = _removed_in_code()
    missing = sorted(removed - _table())
    assert not missing, f"add rows for {missing} to the table of removed names"


def test_migration_table_lists_only_removed_names() -> None:
    """Each name in the table raises its removed-name error."""
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

    stale = sorted(name for name in _table() if not is_removed(name))
    assert not stale, f"the code does not remove {stale}: fix their rows"


# the table of deprecated names ##########################################################

#: code that uses each deprecated name, which must warn and still work
DEPRECATED_USES = {
    "Registry": "from ipyelk.elements import Registry\nwith Registry() as r: r",
    "MarkIndex.context": "from ipyelk.pipes import MarkIndex\nMarkIndex().context",
    "LabelPortSpacing": (
        "from ipyelk.elements.layout_options.port_options import LabelPortSpacing\n"
        "LabelPortSpacing(spacing=3)"
    ),
}


@pytest.mark.parametrize("name", sorted(DEPRECATED_USES))
def test_migration_deprecated_name_warns_and_works(name: str) -> None:
    """Each name in the table of deprecated names warns and keeps working."""
    assert set(DEPRECATED_USES) == _table("migration-deprecated-names")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exec(DEPRECATED_USES[name], {})  # ruff: ignore[exec-builtin]
    # select our own: on ipywidgets 8.0.1 a widget also warns about ipykernel's Comm
    ours = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and f"{name} is deprecated" in str(w.message)
    ]
    assert ours, f"{name} does not warn: {[str(w.message) for w in caught]}"


# the examples ###########################################################################


def _blocks() -> list[dict]:
    """The ``2.x`` and ``3.0`` Python blocks, with their setup and expected text.

    A ``# both versions`` block is the setup of every block under its heading,
    including the blocks of deeper headings.
    """
    blocks: list[dict] = []
    scopes: list[tuple[int, list[str]]] = []
    section = ""
    lines = _guide().splitlines()
    i = 0
    while i < len(lines):
        heading = re.match(r"^(#{2,4}) (.*)", lines[i])
        if heading:
            level = len(heading.group(1))
            scopes = [scope for scope in scopes if scope[0] < level] + [(level, [])]
            section = heading.group(2)
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
        # let the scheduled runs go on until they wait for the browser, which never
        # answers here: the deepest block needs 2 turns of the event loop
        for _ in range(10):
            await asyncio.sleep(0)

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


def _check(block: dict) -> None:
    """A 2.x block shows its quoted text. A 3.0 block, and a 2.x block that quotes no
    text, run and show no error.
    """
    assert block["label"], "start the block with # 2.x, # 3.0 or # both versions"
    lines, raised = _run(block["src"])
    got = _norm(lines)
    if block["label"] == "3.0" or block["expect"] is None:
        label = block["label"]
        assert not raised, f"{block['section']}: the {label} code fails: {got}"
        shown = re.search(r"\w+(Error|Warning):", got)
        assert not shown, f"{block['section']}: the {label} code shows an error: {got}"
        return
    expect = _norm(block["expect"].splitlines())
    if not raised:  # a printed value or a warning: whole lines, not a part of a line
        got, expect = f"\n{got}\n", f"\n{expect}\n"
    assert expect in got, f"{block['section']}: expected {expect!r}, got {got!r}"


@pytest.mark.parametrize("block", _blocks(), ids=itemgetter("id"))
def test_migration_example(block: dict) -> None:
    """Each block of the guide does what the guide says."""
    _check(block)


def test_2x_block_without_text_must_run() -> None:
    """A 2.x block that quotes no text fails the check when it raises."""
    block = {"section": "a test", "label": "2.x", "expect": None}
    _check({**block, "src": "from ipyelk.elements import Label"})
    with pytest.raises(AssertionError, match=r"the 2\.x code fails: ImportError"):
        _check({**block, "src": "from ipyelk.elements import NoSuchName"})
