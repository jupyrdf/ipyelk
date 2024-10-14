"""important project paths

this should not import anything not in py36+ stdlib, or any local paths
"""

# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import itertools
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except Exception:
    import tomli as tomllib

PY_PKG = "ipyelk"

# platform
PLATFORM = os.environ.get("FAKE_PLATFORM", platform.system())
THIS_SUBDIR = {
    "Windows": "win-64",
    "Darwin": "osx-arm64",
    "Linux": "linux-64",
}.get(PLATFORM)
WIN = PLATFORM == "Windows"
OSX = PLATFORM == "Darwin"
LINUX = PLATFORM == "Linux"
UNIX = not WIN
HAS_CONDA_LOCK = shutil.which("conda-lock")


def _get_boolish(name, default="false"):
    return bool(json.loads(os.environ.get(name, default).lower()))


CI = _get_boolish("CI")
WIN_CI = _get_boolish("WIN_CI")
TESTING_IN_CI = _get_boolish("TESTING_IN_CI")
BUILDING_IN_CI = _get_boolish("BUILDING_IN_CI")
IN_BINDER = _get_boolish("IN_BINDER")
IN_RTD = _get_boolish("READTHEDOCS")
PYTEST_ARGS = json.loads(os.environ.get("PYTEST_ARGS", "[]"))

# CI jank
SKIP_CONDA_PREFLIGHT = _get_boolish("SKIP_CONDA_PREFLIGHT")
FORCE_SERIAL_ENV_PREP = _get_boolish("FORCE_SERIAL_ENV_PREP", "true")
# one of: None, wheel or sdist
INSTALL_ARTIFACT = os.environ.get("INSTALL_ARTIFACT")
UTEST_PROCESSES = os.environ.get(
    "UTEST_PROCESSES", os.environ.get("ATEST_PROCESSES", "")
)
IPYELK_PY = os.environ.get("IPYELK_PY", "3.11")

# find root
SCRIPTS = Path(__file__).parent.resolve()
ROOT = SCRIPTS.parent

# git
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
SOURCE_DATE_EPOCH = (
    subprocess.check_output(["git", "log", "-1", "--format=%ct"])
    .decode("utf-8")
    .strip()
)

# top-level stuff
LICENSE = ROOT / "LICENSE.txt"
PY_PROJ = ROOT / "pyproject.toml"
PY_PROJ_DATA = tomllib.loads(PY_PROJ.read_text(encoding="utf-8"))
NODE_MODULES = ROOT / "node_modules"
PACKAGE_JSON = ROOT / "package.json"
JS_PACKAGE_DATA = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
JS_NEEDS_INSTALL_KEYS = [
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "version",
]
JS_PKG = JS_PACKAGE_DATA["name"]
JS_VERSION = JS_PACKAGE_DATA["version"]
YARN_INTEGRITY = NODE_MODULES / ".yarn-state.yml"
YARN_LOCK = ROOT / "yarn.lock"
GH = ROOT / ".github"
DODO = ROOT / "dodo.py"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
ENVS = ROOT / "envs"
CHANGELOG = ROOT / "CHANGELOG.md"
CONDARC = GH / ".condarc"
README = ROOT / "README.md"
DOCS = ROOT / "docs"
BINDER = ROOT / ".binder"
POSTBUILD = BINDER / "postBuild"
BINDER_ENV_YAML = BINDER / "environment.yml"
LITE = ROOT / "lite"
LITE_CONFIG = LITE / "jupyter_lite_config.json"

# envs
ENV_SPECS = GH / "env_specs"
LOCK_ENV_YAML = GH / "lock-environment.yml"
PY_SPECS = sorted(ENV_SPECS.glob("py/*.yml"))
SUBDIR_SPECS = sorted(ENV_SPECS.glob("subdir/*.yml"))
SUBDIR_LOCK_SPECS = sorted(ENV_SPECS.glob("subdir-lock/*.yml"))
ENV_MATRIX = [
    *itertools.product(SUBDIR_SPECS, PY_SPECS, [BINDER_ENV_YAML]),
    *itertools.product(SUBDIR_LOCK_SPECS, [LOCK_ENV_YAML]),
]
EXPLICIT = "@EXPLICIT"
LOCKS = GH / "locks"
PIP_BUILD_ENV = GH / "requirements-build.txt"
LOCKFILE = LOCKS / f"{THIS_SUBDIR}_{IPYELK_PY}_environment.conda.lock"
LOCK_LOCKFILE = LOCKS / f"{THIS_SUBDIR}_lock-environment.conda.lock"
USE_LOCK_ENV = not (BUILDING_IN_CI or IN_RTD or IN_BINDER)
ENV = Path(sys.prefix) if IN_RTD or IN_BINDER else ROOT / f"envs/py_{IPYELK_PY}"
LOCK_ENV = ROOT / "envs/lock"

CONDA_RUN = ["conda", "run", "--live-stream", "--prefix"]
MAMBA_CREATE = ["mamba", "create", "--quiet", "-y", "--prefix"]
CONDA_LOCK = ["conda-lock", "--kind=explicit", "--mamba"]

if BUILDING_IN_CI:
    IN_ENV = []
    HISTORY = PIP_BUILD_ENV
else:
    IN_ENV = [*CONDA_RUN, ENV]
    IN_LOCK_ENV = [*CONDA_RUN, LOCK_ENV]
    HISTORY = ENV / "conda-meta/history"
    LOCK_HISTORY = LOCK_ENV / "conda-meta/history"

# tools
PY = ["python"]
PYM = [*PY, "-m"]
PIP = [*PYM, "pip"]

JLPM = ["jlpm"]
JLPM_INSTALL = [*JLPM]
PREFLIGHT = [*PYM, "scripts.preflight"]
LAB_EXT = ["jupyter", "labextension"]
CONDA_BUILD = ["conda-build"]
LAB = ["jupyter", "lab"]
PRETTIER = [*JLPM, "--silent", "prettier"]
JUPYTERLAB_EXE = [*IN_ENV, "jupyter-lab", "--no-browser"]

# python stuff
PY_SRC = ROOT / "src" / PY_PKG
PY_SCHEMA = PY_SRC / "schema/elkschema.json"
PY_EXT = ROOT / "src/_d/share/jupyter/labextensions/@jupyrdf/jupyter-elk/"
PY_PACKAGE_JSON = PY_EXT / "package.json"

# docs
LITE_JSON = [*LITE.glob("*.json")]
DOCS_BUILD = BUILD / "docs"
DOCS_CONF = DOCS / "conf.py"
DICTIONARY = DOCS / "dictionary.txt"
LITE_BUILD = BUILD / "lite"
LITE_SHA256SUMS = LITE_BUILD / "SHA256SUMS"


# js stuff
JS_LIB = ROOT / "lib"
TSBUILDINFO = BUILD / ".src.tsbuildinfo"
WEBPACKCONFIG = ROOT / "webpack.config.js"
TS_SRC = ROOT / "js"
TS_SCHEMA = TS_SRC / "sprotty" / "json" / "elkschema.ts"
STYLE = ROOT / "style"
ALL_TSCONFIG = [
    ROOT / "tsconfigbase.json",
    ROOT / "tsconfig.json",
    TS_SRC / "tsconfig.json",
]

# tests
EXAMPLES = ROOT / "examples"
EXAMPLE_IPYNB = [
    p for p in EXAMPLES.rglob("*.ipynb") if ".ipynb_checkpoints" not in str(p)
]
EXAMPLE_JSON = [
    p for p in EXAMPLES.rglob("*.json") if ".ipynb_checkpoints" not in str(p)
]
EXAMPLE_PY = [*EXAMPLES.rglob("*.py")]
EXAMPLE_INDEX = EXAMPLES / "_index.ipynb"
EXAMPLE_REQS = EXAMPLES / "requirements.txt"
BUILD_NBHTML = BUILD / "nbsmoke"

# mostly linting
ALL_PY_SRC = [*PY_SRC.rglob("*.py")]
ALL_PY = [
    *ALL_PY_SRC,
    *EXAMPLE_PY,
    *SCRIPTS.rglob("*.py"),
    DOCS_CONF,
    DODO,
    POSTBUILD,
]
ALL_YML = [*ROOT.glob("*.yml"), *GH.rglob("*.yml"), *DOCS.glob("*.yml")]
ALL_JSON = [*ROOT.glob("*.json"), *EXAMPLE_JSON, PY_SCHEMA, *LITE_JSON]
ALL_DOCS_MD = [*DOCS.rglob("*.md")]
ALL_MD = [*ROOT.glob("*.md"), *ALL_DOCS_MD]
ALL_TS = [*TS_SRC.rglob("*.ts")]
ALL_CSS = [*STYLE.rglob("*.css")]
PRETTIER_IGNORE = ROOT / ".prettierignore"
ALL_PRETTIER = [*ALL_YML, *ALL_JSON, *ALL_MD, *ALL_TS, *ALL_CSS, WEBPACKCONFIG]

# built files
OK_RELEASE = BUILD / "release.ok"
OK_PREFLIGHT_CONDA = BUILD / "preflight.conda.ok"
OK_PREFLIGHT_BUILD = BUILD / "preflight.build.ok"
OK_PREFLIGHT_KERNEL = BUILD / "preflight.kernel.ok"
OK_PREFLIGHT_LAB = BUILD / "preflight.lab.ok"
OK_PREFLIGHT_RELEASE = BUILD / "preflight.release.ok"
OK_BLACK = BUILD / "black.ok"
OK_ROBOT_LINT = BUILD / "robot.lint.ok"
OK_LINT = BUILD / "lint.ok"
OK_PYFLAKES = BUILD / "pyflakes.ok"
OK_NBLINT = {nb.name: BUILD / f"nblint.{nb.name}.ok" for nb in EXAMPLE_IPYNB}
OK_PIP_INSTALL = BUILD / "pip_install.ok"
OK_DOCS_PIP_INSTALL = BUILD / "docs_pip_install.ok"
OK_PRETTIER = BUILD / "prettier.ok"
OK_INDEX = BUILD / "index.ok"
OK_LABEXT = BUILD / "labext.ok"
OK_LINKS = BUILD / "links.ok"

HTMLCOV = BUILD / "htmlcov"
HTMLCOV_INDEX = HTMLCOV / "index.html"
PYTEST_COV_THRESHOLD = 17
PYTEST_HTML = BUILD / "pytest.html"
PYTEST_XUNIT = BUILD / "pytest.xunit.xml"

# derived info
PY_VERSION = PY_PROJ_DATA["project"]["version"]

# built artifacts
SDIST = DIST / f"{PY_PKG}-{PY_VERSION}.tar.gz"
WHEEL = DIST / f"{PY_PKG}-{PY_VERSION}-py3-none-any.whl"
NPM_TGZ_STEM = JS_PKG.replace("@", "").replace("/", "-")
NPM_TGZ = DIST / f"{NPM_TGZ_STEM}-{JS_VERSION}.tgz"
EXAMPLE_HTML = [BUILD_NBHTML / p.name.replace(".ipynb", ".html") for p in EXAMPLE_IPYNB]
HASH_DEPS = sorted([SDIST, NPM_TGZ, WHEEL])
SHA256SUMS = DIST / "SHA256SUMS"


# robot testing
ATEST = ROOT / "atest"
ALL_ROBOT = [*ATEST.rglob("*.robot")]
ATEST_OUT = BUILD / "reports/atest"
ATEST_CANARY = BUILD / f"robot.{PLATFORM.lower()}_success.ok"

# docs
DOCS_BUILDINFO = DOCS_BUILD / "html" / ".buildinfo"
DOCS_LINKS = BUILD / "links"
