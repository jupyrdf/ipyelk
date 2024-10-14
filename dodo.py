""" doit tasks for ipyelk

    Generally, you'll just want to `doit`.

    `doit release` does pretty much everything.

    See `doit list` for more options.
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import os
import typing
from pathlib import Path

from doit import create_after
from doit.action import CmdAction
from doit.tools import (
    LongRunning,
    create_folder,
)

from scripts import project as P
from scripts import reporter

os.environ.update(
    MAMBA_NO_BANNER="1",
    NODE_OPTS="--max-old-space-size=4096",
    PIP_DISABLE_PIP_VERSION_CHECK="1",
    PIP_NO_BUILD_ISOLATION="1",
    PYDEVD_DISABLE_FILE_VALIDATION="1",
    PYTHONIOENCODING="utf-8",
    SOURCE_DATE_EPOCH=P.SOURCE_DATE_EPOCH,
)


Paths = typing.List[Path]


def task_watch():
    """watch typescript sources, launch lab, rebuilding as files change"""
    if P.TESTING_IN_CI:
        return

    return dict(
        uptodate=[lambda: False],
        file_dep=[P.OK_PREFLIGHT_LAB],
        actions=[[*P.IN_ENV, "jlpm", "watch"]],
    )



def task_docs():
    """build the docs (mostly as readthedocs would)"""
    yield dict(
        name="sphinx",
        file_dep=[
            P.DOCS_CONF,
            *P.ALL_PY_SRC,
            *P.ALL_MD,
            P.OK_PIP_INSTALL,
            P.LITE_SHA256SUMS,
        ],
        targets=[P.DOCS_BUILDINFO],
        actions=[[*P.IN_ENV, "sphinx-build", "-M", "html", P.DOCS, P.DOCS_BUILD]],
    )


def task_watch_docs():
    """continuously rebuild the docs on change"""
    yield dict(
        uptodate=[lambda: False],
        name="sphinx-autobuild",
        file_dep=[P.DOCS_BUILDINFO, *P.ALL_MD, P.OK_PIP_INSTALL],
        actions=[
            LongRunning(
                [*P.IN_ENV, "sphinx-autobuild", P.DOCS, P.DOCS_BUILD], shell=False
            )
        ],
    )


def _make_spellcheck(dep, html):
    ok = P.BUILD / "spell" / f"{dep.relative_to(html)}.ok"
    return _ok(
        dict(
            name=f"""spell:{dep.relative_to(html)}""".replace("/", "_"),
            doc=f"check spelling in {dep.relative_to(html)}",
            file_dep=[dep, P.DICTIONARY],
            actions=[
                [
                    *P.IN_ENV,
                    "hunspell",
                    "-l",
                    "-d",
                    "en_US,en-GB",
                    "-p",
                    P.DICTIONARY,
                    "-H",
                    dep,
                ]
            ],
        ),
        ok,
    )


@create_after(executed="docs", target_regex=r"build/docs/html/.*\.html")
def task_checkdocs():
    """check spelling and links of build docs HTML."""
    no_check = ["htmlcov", "pytest", "_static"]
    html = P.DOCS_BUILD / "html"
    file_dep = sorted(
        {
            p
            for p in html.rglob("*.html")
            if all(n not in str(p.relative_to(P.DOCS_BUILD)) for n in no_check)
        }
    )

    yield _ok(
        dict(
            name="links",
            doc="check for well-formed links",
            file_dep=file_dep,
            actions=[
                (create_folder, [P.DOCS_LINKS]),
                CmdAction(
                    [
                        *P.IN_ENV,
                        "pytest-check-links",
                        "-vv",
                        *["-p", "no:importnb"],
                        "--check-links-cache",
                        *["--check-links-cache-name", P.DOCS_LINKS],
                        *["-k", "not edit"],
                        "--links-ext=html",
                        *file_dep,
                    ],
                    shell=False,
                    cwd=P.DOCS_BUILD / "html",
                ),
            ],
        ),
        P.OK_LINKS,
    )

    for dep in file_dep:
        yield _make_spellcheck(dep, html)


def _echo_ok(msg):
    def _echo():
        print(msg, flush=True)
        return True

    return _echo


def _ok(task, ok):
    task.setdefault("targets", []).append(ok)
    task["actions"] = [
        lambda: [ok.exists() and ok.unlink(), True][-1],
        *task["actions"],
        lambda: [
            ok.parent.mkdir(exist_ok=True),
            ok.write_text("ok", encoding="utf-8"),
            True,
        ][-1],
    ]
    return task
