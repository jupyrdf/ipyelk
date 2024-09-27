""" doit tasks for ipyelk

    Generally, you'll just want to `doit`.

    `doit release` does pretty much everything.

    See `doit list` for more options.
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import os
import subprocess
import tempfile
import textwrap
import typing
from hashlib import sha256
from pathlib import Path

from doit import create_after
from doit.action import CmdAction
from doit.tools import (
    LongRunning,
    PythonInteractiveAction,
    config_changed,
    create_folder,
)

from scripts import project as P
from scripts import reporter
from scripts import utils as U

os.environ.update(
    MAMBA_NO_BANNER="1",
    NODE_OPTS="--max-old-space-size=4096",
    PIP_DISABLE_PIP_VERSION_CHECK="1",
    PIP_NO_BUILD_ISOLATION="1",
    PYDEVD_DISABLE_FILE_VALIDATION="1",
    PYTHONIOENCODING="utf-8",
    SOURCE_DATE_EPOCH=P.SOURCE_DATE_EPOCH,
)

DOIT_CONFIG = dict(
    backend="sqlite3",
    default_tasks=["binder"],
    par_type="thread",
    reporter=reporter.GithubActionsReporter,
    verbosity=2,
)

Paths = typing.List[Path]


def task_all():
    """do everything except start lab"""

    file_dep = [
        *P.EXAMPLE_HTML,
        P.ATEST_CANARY,
        P.HTMLCOV_INDEX,
        P.PYTEST_HTML,
    ]

    if not P.TESTING_IN_CI:
        file_dep += [
            P.OK_RELEASE,
            P.SHA256SUMS,
        ]

    return dict(
        file_dep=file_dep,
        actions=([_echo_ok("ALL GOOD")]),
    )


def task_lock():
    """create lockfiles from the binder environment and CI excursions."""

    if not P.USE_LOCK_ENV:
        return

    def _lock_comment(env_yamls: Paths) -> str:
        deps = []
        for env_file in reversed(env_yamls):
            found_deps = False
            for line in env_file.read_text(encoding="utf-8").strip().splitlines():
                line = line.strip()
                if line.startswith("dependencies"):
                    found_deps = True
                if not found_deps:
                    continue
                if line.startswith("- "):
                    deps += [line]
        comment = textwrap.indent("\n".join(sorted(set(deps))), "# ")
        return comment

    def _needs_lock(lockfile: Path, env_yamls: Paths) -> bool:
        if not lockfile.exists():
            return True
        lock_text = lockfile.read_text(encoding="utf-8")
        comment = _lock_comment(env_yamls)
        return comment not in lock_text

    def _lock_one(lockfile: Path, env_yamls: typing.List[Path]) -> None:
        if not _needs_lock(lockfile, env_yamls):
            print(f"lockfile up-to-date: {lockfile}")
            return

        lock_args = [*P.CONDA_LOCK]
        comment = _lock_comment(env_yamls)
        for env_file in reversed(env_yamls):
            lock_args += ["--file", env_file]
        platform = next(p.stem for p in env_yamls if "subdir" in p.parent.name)
        lock_args += ["--platform", platform]

        if P.LOCK_HISTORY.exists():
            lock_args = [*P.IN_LOCK_ENV, *lock_args]
        elif not P.HAS_CONDA_LOCK:
            print(
                "Can't bootstrap lockfiles without `conda-lock`, please:\n\n\t"
                "mamba install -c conda-forge conda-lock\n\n"
                "and re-run `doit lock`"
            )
            return False

        str_args = list(map(str, lock_args))
        print(">>>", *str_args)

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            tmp_lock = tdp / f"conda-{platform}.lock"
            subprocess.check_call(str_args, cwd=td)
            raw = tmp_lock.read_text(encoding="utf-8").split(P.EXPLICIT)[1].strip()

        lockfile.parent.mkdir(exist_ok=True, parents=True)
        lockfile.write_text("\n".join([comment, P.EXPLICIT, raw, ""]), encoding="utf-8")

    for env_yamls in P.ENV_MATRIX:
        file_dep = [*env_yamls]
        lock_name = "_".join([f"{p.stem}" for p in env_yamls])
        lockfile = P.LOCKS / f"{lock_name}.conda.lock"

        if not _needs_lock(lockfile, env_yamls):
            continue

        if P.LOCK_ENV_YAML not in env_yamls:
            file_dep += [P.LOCK_HISTORY]

        yield dict(
            name=lock_name,
            actions=[(_lock_one, [lockfile, env_yamls])],
            file_dep=file_dep,
            targets=[lockfile],
        )


def task_preflight():
    """ensure a sane development environment"""
    file_dep = [P.SCRIPTS / "preflight.py"]

    yield _ok(
        dict(
            uptodate=[config_changed({"commit": P.COMMIT})],
            name="conda",
            doc="ensure the conda envs have a chance of working",
            file_dep=file_dep,
            actions=(
                [_echo_ok("skipping preflight, hope you know what you're doing!")]
                if P.SKIP_CONDA_PREFLIGHT
                else [[*P.PREFLIGHT, "conda"]]
            ),
        ),
        P.OK_PREFLIGHT_CONDA,
    )

    yield _ok(
        dict(
            name="kernel",
            doc="ensure the kernel has a chance of working",
            file_dep=[*file_dep, P.HISTORY],
            actions=[[*P.IN_ENV, *P.PREFLIGHT, "kernel"]],
        ),
        P.OK_PREFLIGHT_KERNEL,
    )

    yield _ok(
        dict(
            name="lab",
            file_dep=[*file_dep, P.OK_LABEXT, P.HISTORY],
            actions=[[*P.IN_ENV, *P.PREFLIGHT, "lab"]],
        ),
        P.OK_PREFLIGHT_LAB,
    )

    yield _ok(
        dict(
            name="build",
            doc="ensure the build has a chance of succeeding",
            file_dep=[*file_dep, P.YARN_LOCK, P.HISTORY],
            actions=[[*P.IN_ENV, *P.PREFLIGHT, "build"]],
        ),
        P.OK_PREFLIGHT_BUILD,
    )

    yield _ok(
        dict(
            name="release",
            file_dep=[
                P.CHANGELOG,
                P.NPM_TGZ,
                P.PACKAGE_JSON,
                P.PY_PROJ,
                P.SDIST,
                P.WHEEL,
            ],
            actions=[[*P.IN_ENV, *P.PREFLIGHT, "release"]],
        ),
        P.OK_PREFLIGHT_RELEASE,
    )


def task_binder():
    """get to a minimal interactive environment"""
    return dict(
        file_dep=[P.OK_LABEXT],
        actions=[_echo_ok("ready to run JupyterLab with:\n\n\tdoit lab\n")],
    )


def task_env():
    """prepare project envs"""
    if not P.USE_LOCK_ENV:
        return

    yield dict(
        name="lock",
        file_dep=[P.LOCK_LOCKFILE],
        targets=[P.LOCK_HISTORY],
        actions=[
            [*P.MAMBA_CREATE, P.LOCK_ENV, "--file", P.LOCK_LOCKFILE],
        ],
    )

    yield dict(
        name="dev",
        file_dep=[P.LOCKFILE],
        targets=[P.HISTORY],
        actions=[
            [*P.MAMBA_CREATE, P.ENV, "--file", P.LOCKFILE],
        ],
    )


def task_release():
    """everything we'd need to do to release (except release)"""
    return _ok(
        dict(
            file_dep=[
                P.OK_LINT,
                P.OK_PREFLIGHT_RELEASE,
                P.SHA256SUMS,
            ],
            actions=[_echo_ok("ready to release")],
        ),
        P.OK_RELEASE,
    )


def task_setup():
    """perform all setup activities"""

    _install = ["--no-deps", "--ignore-installed", "-vv"]

    if P.TESTING_IN_CI:
        if P.INSTALL_ARTIFACT == "wheel":
            _install += [P.WHEEL]
        elif P.INSTALL_ARTIFACT == "sdist":
            _install += [P.SDIST]
        else:
            raise RuntimeError(f"Don't know how to install {P.INSTALL_ARTIFACT}")
    else:
        _install += ["-e", "."]

    file_dep = [
        P.HISTORY,
    ]

    if not P.TESTING_IN_CI:
        file_dep += [
            P.PY_SCHEMA,
            P.PY_PROJ,
        ]

    py_actions = [[*P.IN_ENV, *P.PIP, "install", *_install]]

    if not P.IN_RTD:
        # ancient sphinx_rtd_theme wants ancient docutils
        py_actions += [[*P.IN_ENV, *P.PIP, "check"]]

    py_task = _ok(
        dict(
            name="py",
            uptodate=[config_changed({"artifact": P.INSTALL_ARTIFACT})],
            file_dep=file_dep,
            actions=py_actions,
        ),
        P.OK_PIP_INSTALL,
    )

    if P.TESTING_IN_CI and P.INSTALL_ARTIFACT:
        py_task = _ok(py_task, P.OK_LABEXT)
    else:
        py_task["file_dep"] += [P.PY_PACKAGE_JSON]

    yield py_task

    if P.CI and P.YARN_INTEGRITY.exists():
        return

    if not P.TESTING_IN_CI:
        install_deps = [P.PACKAGE_JSON, P.HISTORY]
        install_targets = [P.YARN_INTEGRITY]
        install_args = [*P.JLPM_INSTALL]

        if P.YARN_LOCK.exists():
            install_deps += [P.YARN_LOCK]
        else:
            install_targets += [P.YARN_LOCK]

        if P.CI:
            install_args += ["--frozen-lockfile"]

        install_actions = [[*P.IN_ENV, *install_args]]

        if not P.CI:
            install_actions += [
                [*P.IN_ENV, "jlpm", "yarn-berry-deduplicate", "-s", "fewer", "--fail"]
            ]

        yield dict(
            name="js",
            file_dep=install_deps,
            actions=install_actions,
            targets=install_targets,
        )
        yield _ok(
            dict(
                name="labext",
                actions=[[*P.IN_ENV, *P.LAB_EXT, "develop", "--overwrite", "."]],
                file_dep=[P.OK_PIP_INSTALL, P.PY_PACKAGE_JSON],
            ),
            P.OK_LABEXT,
        )


def task_build():
    """build packages"""
    if P.TESTING_IN_CI:
        return



    ts_dep = [
        *P.ALL_TS,
        *P.ALL_TSCONFIG,
        P.HISTORY,
        P.PACKAGE_JSON,
        P.PY_SCHEMA,
        P.YARN_INTEGRITY,
    ]

    py_dep = [
        *P.ALL_PY_SRC,
        P.HISTORY,
        P.LICENSE,
        P.PY_PACKAGE_JSON,
        P.PY_PROJ,
        P.PY_SCHEMA,
    ]

    if P.USE_LOCK_ENV:
        ts_dep += [P.OK_PRETTIER]
        py_dep += [P.OK_LINT]

    yield dict(
        name="ts",
        file_dep=ts_dep,
        actions=[[*P.IN_ENV, *P.JLPM, "build:ts"]],
        targets=[P.TSBUILDINFO],
    )
    
    yield dict(
        name="schema",
        file_dep=[P.YARN_INTEGRITY, P.TS_SCHEMA, P.HISTORY],
        actions=[[*P.IN_ENV, *P.JLPM, "schema"]],
        targets=[P.PY_SCHEMA],
    )    

    yield dict(
        name="ext",
        actions=[[*P.IN_ENV, *P.JLPM, "build:ext"]],
        file_dep=[P.TSBUILDINFO, *P.ALL_CSS, P.WEBPACKCONFIG],
        targets=[P.PY_PACKAGE_JSON],
    )

    yield dict(
        name="pack",
        file_dep=[P.TSBUILDINFO, P.PACKAGE_JSON, *P.ALL_CSS, P.README, P.LICENSE],
        actions=[
            (create_folder, [P.DIST]),
            CmdAction([*P.IN_ENV, "npm", "pack", ".."], shell=False, cwd=str(P.DIST)),
        ],
        targets=[P.NPM_TGZ],
    )

    yield dict(
        name="py",
        uptodate=[config_changed(dict(SOURCE_DATE_EPOCH=P.SOURCE_DATE_EPOCH))],
        file_dep=py_dep,
        actions=[[*P.IN_ENV, "flit", "--debug", "build"]],
        targets=[P.WHEEL, P.SDIST],
    )

    def _run_hash():
        # mimic sha256sum CLI
        if P.SHA256SUMS.exists():
            P.SHA256SUMS.unlink()

        lines = []

        for p in P.HASH_DEPS:
            lines += ["  ".join([sha256(p.read_bytes()).hexdigest(), p.name])]

        output = "\n".join(lines)
        print(output)
        P.SHA256SUMS.write_text(output)

    yield dict(
        name="hash",
        file_dep=P.HASH_DEPS,
        targets=[P.SHA256SUMS],
        actions=[_run_hash],
    )


def task_pytest():
    """run python unit tests"""
    utest_args = [
        *P.IN_ENV,
        "pytest",
        "--cov-fail-under",
        str(P.PYTEST_COV_THRESHOLD),
    ]

    if P.UTEST_PROCESSES:
        utest_args += ["-n", P.UTEST_PROCESSES]

    if P.PYTEST_ARGS:
        utest_args += P.PYTEST_ARGS

    yield dict(
        name="utest",
        doc="run unit tests with pytest",
        uptodate=[config_changed(dict(COMMIT=P.COMMIT, args=P.PYTEST_ARGS))],
        file_dep=[*P.ALL_PY_SRC, P.PY_PROJ, P.OK_PIP_INSTALL],
        targets=[P.HTMLCOV_INDEX, P.PYTEST_HTML, P.PYTEST_XUNIT],
        actions=[
            utest_args,
            lambda: U.strip_timestamps(
                *P.HTMLCOV.rglob("*.html"), P.PYTEST_HTML, slug=P.COMMIT
            ),
        ],
    )


def task_test():
    """run all the notebooks"""

    def _nb_test(nb):
        def _test():
            env = dict(os.environ)
            env.update(IPYELK_TESTING="true")
            args = [
                *P.IN_ENV,
                "jupyter",
                "nbconvert",
                "--to",
                "html",
                "--output-dir",
                P.BUILD_NBHTML,
                "--execute",
                "--ExecutePreprocessor.timeout=1200",
                nb,
            ]
            return CmdAction(args, env=env, shell=False)

        file_dep = [
            *P.ALL_PY_SRC,
            *P.EXAMPLE_IPYNB,
            *P.EXAMPLE_JSON,
            P.HISTORY,
            P.OK_PIP_INSTALL,
            P.OK_PREFLIGHT_KERNEL,
            *([] if P.TESTING_IN_CI else [P.OK_NBLINT[nb.name]]),
        ]

        if not P.TESTING_IN_CI:
            file_dep += [
                P.PY_SCHEMA,
            ]

        return dict(
            name=f"nb:{nb.name}".replace(" ", "_").replace(".ipynb", ""),
            file_dep=file_dep,
            actions=[_test()],
            targets=[P.BUILD_NBHTML / nb.name.replace(".ipynb", ".html")],
        )

    for nb in P.EXAMPLE_IPYNB:
        yield _nb_test(nb)

    def _pabot_logs():
        for robot_out in sorted(P.ATEST_OUT.rglob("robot_*.out")):
            print(f"\n[{robot_out.relative_to(P.ROOT)}]")
            print(robot_out.read_text() or "<EMPTY>")

    yield dict(
        name="atest",
        file_dep=[
            *P.ALL_PY_SRC,
            *P.ALL_ROBOT,
            *P.EXAMPLE_IPYNB,
            *P.EXAMPLE_JSON,
            P.OK_PIP_INSTALL,
            P.OK_PREFLIGHT_LAB,
            P.SCRIPTS / "atest.py",
            *([] if P.TESTING_IN_CI else [P.OK_ROBOT_LINT, *P.OK_NBLINT.values()]),
        ],
        task_dep=["pytest"],
        actions=[[*P.IN_ENV, *P.PYM, "scripts.atest"], _pabot_logs],
        targets=[P.ATEST_CANARY],
    )


def task_lint():
    """format all source files"""
    if P.TESTING_IN_CI:
        return

    yield _ok(
        dict(
            name="black",
            file_dep=[*P.ALL_PY, P.HISTORY],
            actions=[
                [*P.IN_ENV, "isort", "--quiet", "--ac", *P.ALL_PY],
                [*P.IN_ENV, "black", "--quiet", *P.ALL_PY],
            ],
        ),
        P.OK_BLACK,
    )
    yield _ok(
        dict(
            name="pyflakes",
            file_dep=[*P.ALL_PY, P.OK_BLACK],
            actions=[[*P.IN_ENV, "pyflakes", *P.ALL_PY]],
        ),
        P.OK_PYFLAKES,
    )
    yield _ok(
        dict(
            name="prettier",
            uptodate=[
                config_changed(
                    dict(
                        conf=P.JS_PACKAGE_DATA["prettier"],
                        script=P.JS_PACKAGE_DATA["scripts"]["lint:prettier"],
                    )
                )
            ],
            file_dep=[
                *P.ALL_PRETTIER,
                P.HISTORY,
                P.PRETTIER_IGNORE,
                P.YARN_INTEGRITY,
                
            ],
            actions=[
                [*P.IN_ENV, "npm", "run", "lint:prettier"],
            ],
        ),
        P.OK_PRETTIER,
    )

    for nb in P.EXAMPLE_IPYNB:
        yield _ok(
            dict(
                name=f"nblint:{nb.name}".replace(" ", "_").replace(".ipynb", ""),
                file_dep=[P.YARN_INTEGRITY, nb, P.HISTORY, P.OK_BLACK],
                actions=[
                    [*P.IN_ENV, *P.PYM, "scripts.nblint", nb],
                    [*P.IN_ENV, "black", "--quiet", nb],
                ],
            ),
            P.OK_NBLINT[nb.name],
        )

    yield _ok(
        dict(
            name="robot",
            file_dep=[
                *P.ALL_ROBOT,
                *P.ALL_PY_SRC,
                *P.ALL_TS,
                P.SCRIPTS / "atest.py",
                P.OK_PYFLAKES,
                P.HISTORY,
            ],
            actions=[
                [*P.IN_ENV, *P.PYM, "robotidy", *P.ALL_ROBOT],
                [*P.IN_ENV, *P.PYM, "scripts.atest", "--dryrun"],
            ],
        ),
        P.OK_ROBOT_LINT,
    )

    index_src = P.EXAMPLE_INDEX.read_text(encoding="utf-8")

    def _make_index_check(ex):
        def _check():
            md = f"(./{ex.name})"

            if md not in index_src:
                print(f"{ex.name} link missing in _index.ipynb")
                return False

        return _check

    yield _ok(
        dict(
            name="index",
            file_dep=P.EXAMPLE_IPYNB,
            actions=[
                _make_index_check(ex) for ex in P.EXAMPLE_IPYNB if ex != P.EXAMPLE_INDEX
            ],
        ),
        P.OK_INDEX,
    )

    yield _ok(
        dict(
            name="all",
            actions=[_echo_ok("all ok")],
            file_dep=[
                P.OK_BLACK,
                P.OK_PRETTIER,
                P.OK_PYFLAKES,
                P.OK_ROBOT_LINT,
                P.OK_INDEX,
            ],
        ),
        P.OK_LINT,
    )


def task_lab():
    """run JupyterLab "normally" (not watching sources)"""

    def lab():
        proc = subprocess.Popen(
            list(map(str, P.JUPYTERLAB_EXE)),
            stdin=subprocess.PIPE,
        )
        try:
            proc.wait()
        except KeyboardInterrupt:
            print("attempting to stop lab, you may want to check your process monitor")
            proc.terminate()
            proc.communicate(b"y\n")

        proc.wait()
        return True

    return dict(
        uptodate=[lambda: False],
        file_dep=[P.OK_PIP_INSTALL, P.OK_PREFLIGHT_LAB],
        actions=[PythonInteractiveAction(lab)],
    )


def task_watch():
    """watch typescript sources, launch lab, rebuilding as files change"""
    if P.TESTING_IN_CI:
        return

    return dict(
        uptodate=[lambda: False],
        file_dep=[P.OK_PREFLIGHT_LAB],
        actions=[[*P.IN_ENV, "jlpm", "watch"]],
    )


def task_lite():
    """build the jupyterlite site"""

    yield dict(
        name="pip:install",
        file_dep=[P.OK_PIP_INSTALL],
        actions=[[*P.IN_ENV, *P.PIP, "install", "--no-deps", *P.LITE_SPEC]],
    )

    yield dict(
        name="build",
        file_dep=[
            *P.EXAMPLE_IPYNB,
            *P.EXAMPLE_JSON,
            *P.LITE_JSON,
            P.EXAMPLE_REQS,
            P.WHEEL,
        ],
        task_dep=["lite:pip:install"],
        targets=[P.LITE_SHA256SUMS],
        actions=[
            CmdAction(
                [*P.IN_ENV, "jupyter", "lite", "build"], shell=False, cwd=str(P.LITE)
            ),
            CmdAction(
                [
                    *P.IN_ENV,
                    "jupyter",
                    "lite",
                    "doit",
                    "--",
                    "pre_archive:report:SHA256SUMS",
                ],
                shell=False,
                cwd=str(P.LITE),
            ),
        ],
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
