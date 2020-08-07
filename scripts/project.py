""" important project paths

    this should not import anything not in py36+ stdlib, or any local paths
"""
import json
import os
import platform
import re
import shutil
from pathlib import Path

PY_PKG = "ipyelk"

# platform
PLATFORM = os.environ.get("FAKE_PLATFORM", platform.system())
WIN = PLATFORM == "Windows"
OSX = PLATFORM == "Darwin"
UNIX = not WIN

# CI jank
SKIP_CONDA_PREFLIGHT = bool(json.loads(os.environ.get("SKIP_CONDA_PREFLIGHT", "false")))
FORCE_SERIAL_ENV_PREP = bool(
    json.loads(os.environ.get("FORCE_SERIAL_ENV_PREP", "true"))
)

# find root
SCRIPTS = Path(__file__).parent.resolve()
ROOT = SCRIPTS.parent

# top-level stuff
SETUP_PY = ROOT / "setup.py"
SETUP_CFG = ROOT / "setup.cfg"
NODE_MODULES = ROOT / "node_modules"
PACKAGE_JSON = ROOT / "package.json"
JS_PACKAGE_DATA = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
JS_PKG = JS_PACKAGE_DATA["name"]
JS_VERSION = JS_PACKAGE_DATA["version"]
YARN_INTEGRITY = NODE_MODULES / ".yarn-integrity"
YARN_LOCK = ROOT / "yarn.lock"
EXTENSIONS = ROOT / "labextensions.txt"
CI = ROOT / ".github"
DODO = ROOT / "dodo.py"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
ENVS = ROOT / "envs"
PROJ_LOCK = ROOT / "anaconda-project-lock.yml"

# tools
PY = ["python"]
PYM = [*PY, "-m"]
PIP = [*PYM, "pip"]

JLPM = ["jlpm"]
JLPM_INSTALL = [*JLPM, "--ignore-optional", "--prefer-offline"]
PREFLIGHT = ["python", "-m", "scripts.preflight"]
YARN = [shutil.which("yarn") or shutil.which("yarn.cmd")]
LAB_EXT = ["jupyter", "labextension"]
CONDA_BUILD = ["conda-build"]
LAB = ["jupyter", "lab"]
AP = ["anaconda-project"]
AP_PREP = [*AP, "prepare", "--env-spec"]
APR = [*AP, "run", "--env-spec"]
APR_DEFAULT = [*APR, "default"]
PRETTIER = [*JLPM, "--silent", "prettier"]

# env stuff
OK_ENV = {env: BUILD / f"prep_{env}.ok" for env in ["default"]}

# python stuff
PY_SRC = ROOT / PY_PKG
PY_SCHEMA = PY_SRC / "schema/elkschema.json"
VERSION_PY = PY_SRC / "_version.py"

# js stuff
JS_LIB = ROOT / "lib"
TSBUILDINFO = JS_LIB / ".tsbuildinfo"
TS_SRC = ROOT / "src"
STYLE = ROOT / "style"

# lab stuff
LAB_APP_DIR = ENVS / "default/share/jupyter/lab"
LAB_STAGING = LAB_APP_DIR / "staging"
LAB_LOCK = LAB_STAGING / "yarn.lock"
LAB_STATIC = LAB_APP_DIR / "static"
LAB_INDEX = LAB_STATIC / "index.html"

# tests
EXAMPLES = ROOT / "examples"
EXAMPLE_IPYNB = [
    p for p in EXAMPLES.rglob("*.ipynb") if ".ipynb_checkpoints" not in str(p)
]
EXAMPLE_PY = [*EXAMPLES.rglob("*.py")]
DIST_NBHTML = DIST / "nbsmoke"

# mostly linting
ALL_PY_SRC = [*PY_SRC.rglob("*.py")]
ALL_PY = [DODO, *ALL_PY_SRC, *EXAMPLE_PY, *SCRIPTS.rglob("*.py")]
ALL_YML = [*ROOT.glob("*.yml"), *CI.rglob("*.yml")]
ALL_JSON = [*ROOT.glob("*.json"), PY_SCHEMA]
ALL_MD = [*ROOT.glob("*.md")]
ALL_TS = [*TS_SRC.rglob("*.ts")]
ALL_CSS = [*STYLE.rglob("*.css")]
ALL_PRETTIER = [*ALL_YML, *ALL_JSON, *ALL_MD, *ALL_TS, *ALL_CSS]

# built files
OK_RELEASE = BUILD / "release.ok"
OK_PREFLIGHT_CONDA = BUILD / "preflight.conda.ok"
OK_PREFLIGHT_KERNEL = BUILD / "preflight.kernel.ok"
OK_PREFLIGHT_LAB = BUILD / "preflight.lab.ok"
NBLINT_HASHES = BUILD / "nblint.hashes"
OK_BLACK = BUILD / "black.ok"
OK_FLAKE8 = BUILD / "flake8.ok"
OK_ISORT = BUILD / "isort.ok"
OK_LINT = BUILD / "lint.ok"
OK_PYFLAKES = BUILD / "pyflakes.ok"
OK_NBLINT = BUILD / "nblint.ok"
OK_PIP_INSTALL_E = BUILD / "pip_install_e.ok"
OK_PRETTIER = BUILD / "prettier.ok"

# derived info
PY_VERSION = re.findall(r'''__version__ = "(.*)"''', VERSION_PY.read_text())[0]


# built artifacts
SDIST = DIST / f"{PY_PKG}-{PY_VERSION}.tar.gz"
WHEEL = DIST / f"{PY_PKG}-{PY_VERSION}-py3-none-any.whl"
NPM_TGZ_STEM = JS_PKG.replace("@", "").replace("/", "-")
NPM_TGZ = DIST / f"{NPM_TGZ_STEM}-{JS_VERSION}.tgz"
EXAMPLE_HTML = [DIST_NBHTML / p.name.replace(".ipynb", ".html") for p in EXAMPLE_IPYNB]
