"""helper for anaconda-project with mamba and a 'clean' condarc"""
# Copyright (c) 2022 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
CONDARC = ROOT / ".github" / ".condarc"

MAMBA = shutil.which("mamba")


def lock():
    env = dict(os.environ)
    if "CONDARC" not in env:
        env["CONDARC"] = str(CONDARC)
    if MAMBA:
        env["CONDA_EXE"] = MAMBA

    for envspec in ["default", "atest", "docs"]:
        subprocess.check_call(["anaconda-project", "update", "-n", envspec], env=env)


if __name__ == "__main__":
    sys.exit(lock())
