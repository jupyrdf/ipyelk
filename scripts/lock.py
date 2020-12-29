import sys
import subprocess
import os
import shutil
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
CONDARC = ROOT / ".github" / ".condarc"

MAMBA = shutil.which("mamba")


def lock():
    env = dict(os.environ, CONDARC=str(CONDARC))
    if MAMBA:
        env["CONDA_EXE"] = MAMBA

    for envspec in ["default", "atest"]:
        subprocess.check_call(["anaconda-project", "update", "-n", envspec], env=env)


if __name__ == "__main__":
    sys.exit(lock())
