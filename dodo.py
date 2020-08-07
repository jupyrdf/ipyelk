""" doit tasks for ipyradiant

    Generally, you'll just want to `doit`.

    `doit release` does pretty much everything.

    See `doit list` for more options.
"""
import os
import subprocess

import scripts.project as P
from doit.action import CmdAction
from doit.tools import PythonInteractiveAction, config_changed

os.environ["PYTHONIOENCODING"] = "utf-8"

DOIT_CONFIG = {
    "backend": "sqlite3",
    "verbosity": 2,
    "par_type": "thread",
    "default_tasks": ["binder"],
}

COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8")


def task_preflight():
    """ ensure a sane development environment
    """
    file_dep = [P.PROJ_LOCK, P.SCRIPTS / "preflight.py"]

    yield _ok(
        dict(
            uptodate=[config_changed({"commit": COMMIT})],
            name="conda",
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
            file_dep=[*file_dep, P.OK_ENV["default"]],
            actions=[[*P.APR_DEFAULT, *P.PREFLIGHT, "kernel"]],
        ),
        P.OK_PREFLIGHT_KERNEL,
    )

    yield _ok(
        dict(
            name="lab",
            file_dep=[*file_dep, P.LAB_INDEX, P.OK_ENV["default"]],
            actions=[[*P.APR_DEFAULT, *P.PREFLIGHT, "lab"]],
        ),
        P.OK_PREFLIGHT_LAB,
    )


def task_binder():
    """ get to a minimal interactive environment
    """
    return dict(
        file_dep=[
            P.LAB_INDEX,
            P.OK_PIP_INSTALL_E,
            P.OK_PREFLIGHT_KERNEL,
            P.OK_PREFLIGHT_LAB,
        ],
        actions=[_echo_ok("ready to run JupyterLab with:\n\n\tdoit lab\n")],
    )


def task_env():
    """ prepare project envs
    """
    envs = ["default"]
    for i, env in enumerate(envs):
        file_dep = [P.PROJ_LOCK, P.OK_PREFLIGHT_CONDA]
        if P.FORCE_SERIAL_ENV_PREP and i:
            file_dep += [P.OK_ENV[envs[i - 1]]]
        yield _ok(
            dict(name=env, file_dep=file_dep, actions=[[*P.AP_PREP, env]]),
            P.OK_ENV[env],
        )


def task_release():
    """ everything we'd need to do to release (except release)
    """
    return _ok(
        dict(
            file_dep=[P.OK_PIP_INSTALL_E, P.OK_LINT, P.WHEEL, *P.EXAMPLE_HTML],
            actions=[_echo_ok("ready to release")],
        ),
        P.OK_RELEASE,
    )


def task_setup():
    """ perform all setup activities
    """
    yield _ok(
        dict(
            name="py",
            file_dep=[P.SETUP_PY, P.SETUP_CFG, P.OK_ENV["default"], P.PY_SCHEMA],
            actions=[
                [*P.APR_DEFAULT, *P.PIP, "install", "-e", ".", "--no-deps"],
                [*P.APR_DEFAULT, *P.PIP, "check"],
            ],
        ),
        P.OK_PIP_INSTALL_E,
    )

    yield dict(
        name="js",
        file_dep=[P.YARN_LOCK, P.PACKAGE_JSON, P.OK_ENV["default"]],
        actions=[[*P.APR_DEFAULT, *P.JLPM_INSTALL]],
        targets=[P.YARN_INTEGRITY],
    )


def task_build():
    """ build packages
    """

    yield dict(
        name="ts",
        file_dep=[P.YARN_INTEGRITY, *P.ALL_TS, P.OK_ENV["default"]],
        actions=[[*P.APR_DEFAULT, *P.JLPM, "build"]],
        targets=[P.TSBUILDINFO, P.PY_SCHEMA],
    )

    yield dict(
        name="pack",
        file_dep=[P.TSBUILDINFO, P.PACKAGE_JSON],
        actions=[[*P.APR_DEFAULT, "ext:pack"]],
        targets=[P.NPM_TGZ],
    )

    yield dict(
        name="py",
        file_dep=[
            *P.ALL_PY_SRC,
            P.SETUP_CFG,
            P.SETUP_PY,
            P.OK_LINT,
            P.OK_ENV["default"],
            P.PY_SCHEMA,
        ],
        actions=[
            [*P.APR_DEFAULT, *P.PY, "setup.py", "sdist"],
            [*P.APR_DEFAULT, *P.PY, "setup.py", "bdist_wheel"],
        ],
        targets=[P.WHEEL, P.SDIST],
    )


def task_test():
    """ run all the notebooks
    """

    def _nb_test(nb):
        def _test():
            env = dict(os.environ)
            env.update(IPYRADIANT_TESTING="true")
            args = [
                *P.APR_DEFAULT,
                "jupyter",
                "nbconvert",
                "--output-dir",
                P.DIST_NBHTML,
                "--execute",
                "--ExecutePreprocessor.timeout=1200",
                nb,
            ]
            return CmdAction(args, env=env, shell=False)

        return dict(
            name=f"nb:{nb.name}".replace(" ", "_").replace(".ipynb", ""),
            file_dep=[
                *P.EXAMPLE_IPYNB,
                P.OK_NBLINT,
                P.OK_ENV["default"],
                P.OK_PIP_INSTALL_E,
                P.OK_PREFLIGHT_KERNEL,
            ],
            actions=[_test()],
            targets=[P.DIST_NBHTML / nb.name.replace(".ipynb", ".html")],
        )

    for nb in P.EXAMPLE_IPYNB:
        yield _nb_test(nb)


def task_lint():
    """ format all source files
    """

    yield _ok(
        dict(
            name="isort",
            file_dep=[*P.ALL_PY, P.OK_ENV["default"]],
            actions=[[*P.APR_DEFAULT, "isort", "-rc", *P.ALL_PY]],
        ),
        P.OK_ISORT,
    )
    yield _ok(
        dict(
            name="black",
            file_dep=[*P.ALL_PY, P.OK_ISORT],
            actions=[[*P.APR_DEFAULT, "black", "--quiet", *P.ALL_PY]],
        ),
        P.OK_BLACK,
    )
    yield _ok(
        dict(
            name="flake8",
            file_dep=[*P.ALL_PY, P.OK_BLACK],
            actions=[[*P.APR_DEFAULT, "flake8", *P.ALL_PY]],
        ),
        P.OK_FLAKE8,
    )
    yield _ok(
        dict(
            name="pyflakes",
            file_dep=[*P.ALL_PY, P.OK_BLACK],
            actions=[[*P.APR_DEFAULT, "pyflakes", *P.ALL_PY]],
        ),
        P.OK_PYFLAKES,
    )
    yield _ok(
        dict(
            name="prettier",
            file_dep=[P.YARN_INTEGRITY, *P.ALL_PRETTIER, P.OK_ENV["default"]],
            actions=[[*P.APR_DEFAULT, "npm", "run", "lint:prettier"]],
        ),
        P.OK_PRETTIER,
    )
    yield _ok(
        dict(
            name="nblint",
            file_dep=[P.YARN_INTEGRITY, *P.EXAMPLE_IPYNB, P.OK_ENV["default"]],
            actions=[[*P.APR_DEFAULT, *P.PYM, "scripts.nblint", *P.EXAMPLE_IPYNB]],
            targets=[P.NBLINT_HASHES],
        ),
        P.OK_NBLINT,
    )
    yield _ok(
        dict(
            name="all",
            actions=[_echo_ok("all ok")],
            file_dep=[
                P.OK_BLACK,
                P.OK_FLAKE8,
                P.OK_ISORT,
                P.OK_PRETTIER,
                P.OK_PYFLAKES,
                P.OK_NBLINT,
            ],
        ),
        P.OK_LINT,
    )


def task_lab_build():
    """ do a "production" build of lab
    """
    exts = [
        line.strip()
        for line in P.EXTENSIONS.read_text().strip().splitlines()
        if line and not line.startswith("#")
    ]

    def _clean():
        _call([*P.APR_DEFAULT, "jlpm", "cache", "clean"])
        _call([*P.APR_DEFAULT, *P.LAB, "clean"])

        return True

    install = [*P.APR_DEFAULT, *P.LAB_EXT, "install", "--debug", "--no-build"]
    list_ext = [*P.APR_DEFAULT, *P.LAB_EXT, "list"]

    yield dict(
        name="extensions",
        file_dep=[P.EXTENSIONS, P.NPM_TGZ],
        actions=[
            _clean,
            [*install, *exts],
            list_ext,
            [*install, P.NPM_TGZ],
            list_ext,
            [*P.APR_DEFAULT, "lab:build"],
            list_ext,
        ],
        targets=[P.LAB_INDEX],
    )


def task_lab():
    """ run JupyterLab "normally" (not watching sources)
    """

    def lab():
        proc = subprocess.Popen(
            list(map(str, [*P.APR_DEFAULT, "lab"])), stdin=subprocess.PIPE
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
        file_dep=[P.LAB_INDEX, P.OK_PIP_INSTALL_E, P.OK_PREFLIGHT_LAB],
        actions=[PythonInteractiveAction(lab)],
    )


def task_watch():
    """ watch typescript sources, launch lab, rebuilding as files change
    """

    def _watch():
        proc = subprocess.Popen(
            list(map(str, [*P.APR_DEFAULT, "watch"])), stdin=subprocess.PIPE
        )

        try:
            proc.wait()
        except KeyboardInterrupt:
            pass

        proc.wait()
        return True

    return dict(
        uptodate=[lambda: False],
        file_dep=[P.OK_PIP_INSTALL_E],
        actions=[PythonInteractiveAction(_watch)],
    )


def task_all():
    """ do everything except start lab
    """
    return dict(
        file_dep=[P.OK_RELEASE, P.OK_PREFLIGHT_LAB], actions=([_echo_ok("ALL GOOD")]),
    )


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
        lambda: [ok.parent.mkdir(exist_ok=True), ok.write_text("ok"), True][-1],
    ]
    return task


def _call(args, **kwargs):
    if "cwd" in kwargs:
        kwargs["cwd"] = str(kwargs["cwd"])
    if "env" in kwargs:
        kwargs["env"] = {k: str(v) for k, v in kwargs["env"].items()}
    args = list(map(str, args))
    print("\n>>>", " ".join(args), "\n", flush=True)
    return subprocess.call(args, **kwargs)
