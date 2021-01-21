""" ensure the development environment is sane

    be careful about imports here:
"""

# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint

from . import project as P

BAD_PATH_RE = r"[^a-zA-Z\d_\-\.\\/]"
ROOT_RECOMMEND = (
    f"c:\\git\\{P.PY_PKG}" if P.WIN else os.path.expanduser(f"~/git/{P.PY_PKG}")
)
MC3_RECOMMEND = "c:\\mc3" if P.WIN else os.path.expanduser("~/mc3")
ARBITRARY_PATH_LENGTH = 32 if P.WIN else 64
NOT_DEFINED = "!NOT DEFINED!"
DEFAULT_KERNEL_NAME = "python3"

COPYRIGHT = f"Copyright (c) {datetime.now().year} Dane Freeman."
LICENSE = "Distributed under the terms of the Modified BSD License."


def check_path(path, name=None, message=None, check_len=False):
    print(f"Checking sanity of {name or path}...", flush=True)
    errors = {}

    if path == NOT_DEFINED:
        errors["not defined"] = path
    else:
        drive, rest = os.path.splitdrive(str(Path(path).resolve()))

        path_len = len(str(path))

        if not path_len:
            errors["not_defined"] = True
        elif check_len and path_len > ARBITRARY_PATH_LENGTH:
            errors["length"] = path_len

        bad_path_matches = re.findall(BAD_PATH_RE, rest)

        if bad_path_matches:
            errors["bad_characters"] = bad_path_matches

    if errors:
        print(f"... {len(errors)} problems with {name or path}")
        return [{"path": str(path), "message": str(message), "errors": errors}]

    return []


def check_drives(path_a, path_b, message):
    print(f"Checking drives of '{path_a}' and '{path_b}'...")
    a_drive, a_rest = os.path.splitdrive(str(path_a))
    b_drive, b_rest = os.path.splitdrive(str(path_a))

    if a_drive != b_drive:
        print("...drives are no good")
        return [{"paths": [path_a, path_b]}]
    return []


def preflight_conda():
    """this should only run from the `base` env"""

    conda_prefix = os.environ.get("CONDA_PREFIX", NOT_DEFINED)
    errors = [
        *check_path(
            path=P.ROOT,
            name="repo location",
            message=f"please check out to a sane location, e.g {ROOT_RECOMMEND}",
            check_len=True,
        ),
        *check_path(
            path=os.environ.get("CONDA_PREFIX", NOT_DEFINED),
            message=(
                "please install and activate miniconda3 in a sane location"
                f" e.g. {MC3_RECOMMEND}"
            ),
            check_len=True,
        ),
        *check_drives(
            P.ROOT,
            conda_prefix,
            "please ensure miniconda3 and this repo are on the same"
            " physical drive/volume",
        ),
    ]

    if errors:
        pprint(errors)

    print(">>> OK conda!")

    return len(errors)


def preflight_build():
    yarn_lock_errors = []
    for line in P.YARN_LOCK.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("resolved ") and "https://" not in line:
            yarn_lock_errors += line

    if yarn_lock_errors:
        print(f"Encountered non-https resolutions in {P.YARN_LOCK}")
        print("\n".join(yarn_lock_errors))
        print(
            """Perhaps try:
            rm -rf node_modules .yarn-packages yarn.lock
            anaconda-project run jlpm cache clean
            anaconda-project run jlpm
            doit preflight:build
            """
        )

    return len(yarn_lock_errors)


def preflight_kernel():
    """this should only run from the `dev` env"""
    print("Checking kernel list...", flush=True)
    raw = subprocess.check_output(["jupyter", "kernelspec", "list", "--json"])
    specs = json.loads(raw.decode("utf-8"))["kernelspecs"]

    print(f"Checking {DEFAULT_KERNEL_NAME}...", flush=True)
    default_kernel = specs.get(DEFAULT_KERNEL_NAME)

    if default_kernel is None:
        print(f"The {DEFAULT_KERNEL_NAME} kernel is not available at all!")
        return 1

    print(f"Checking {DEFAULT_KERNEL_NAME} python...", flush=True)

    spec_py = default_kernel["spec"]["argv"][0]

    if Path(spec_py).resolve() != Path(sys.executable).resolve():
        pprint(spec_py)
        print(f"The {DEFAULT_KERNEL_NAME} does not use {sys.executable}!")
        return 2

    print(">>> OK kernel!")
    return 0


def preflight_lab():
    proc = subprocess.Popen(
        ["jupyter", "labextension", "list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()
    name = P.JS_PACKAGE_DATA["name"]

    for line in (out + err).decode("utf-8").splitlines():
        if name in line and "OK" in line and "enabled" in line:
            print(">>> OK lab")
            return 0
    print("The labextension is not enabled")
    return 1


def preflight_release():
    problems = []
    changelog = P.CHANGELOG.read_text(encoding="utf-8")

    print("Checking CHANGELOG...", flush=True)
    changelog_versions = [
        f"## {P.PY_PKG} {P.PY_VERSION}",
        "## {name} {version}".format(**P.JS_PACKAGE_DATA),
    ]

    for version in changelog_versions:
        if version not in changelog:
            problems += [f"- Not found in CHANGELOG.md: {version}"]

    print("Checking widget spec versions...", flush=True)
    tokens_ts = P.TS_SRC / "tokens.ts"
    ts_version = re.findall(r"""VERSION = '(.*?)'""", tokens_ts.read_text())[0]
    py_version = re.findall(
        r"""EXTENSION_SPEC_VERSION = "([^"]+)""", P.VERSION_PY.read_text()
    )[0]

    if ts_version != py_version:
        problems += [
            "python EXTENSION_SPEC_VERSION do not match typescript VERSION"
            f"\n> {py_version} vs {ts_version}"
        ]

    print("Checking copyright/license headers...")
    for any_src in [*P.ALL_PY, *P.ALL_CSS, *P.ALL_TS]:
        any_text = any_src.read_text()
        if COPYRIGHT not in any_text:
            problems += [f"{any_src.relative_to(P.ROOT)} missing copyright info"]
        if LICENSE not in any_text:
            problems += [f"{any_src.relative_to(P.ROOT)} missing license info"]

    print(len(problems), "problem(s) found")

    if problems:
        [print(problem) for problem in problems]

    return len(problems)


def preflight(stage):
    if stage == "conda":
        return preflight_conda()
    elif stage == "build":
        return preflight_build()
    elif stage == "kernel":
        return preflight_kernel()
    elif stage == "lab":
        return preflight_lab()
    elif stage == "release":
        return preflight_release()

    print(f"Don't know how to preflight: {stage}")
    return 1


if __name__ == "__main__":
    sys.exit(preflight(sys.argv[1]))
