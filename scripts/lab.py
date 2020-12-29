""" handle lingering issues with jupyterlab 1.x build
"""
# Copyright (c) 2020 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

JLPM = shutil.which("jlpm")


def watch():
    """after preparing, start watchers"""
    print("watching src...", flush=True)
    ts = subprocess.Popen([JLPM, "watch"], cwd=str(ROOT))

    def stop():
        print("stopping watchers...", flush=True)
        ts.terminate()
        ts.wait()
        print("...watchers stopped!", flush=True)

    print("Built, starting lab...", flush=True)

    lab = subprocess.Popen(
        ["jupyter", "lab", "--no-browser", "--debug"],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
    )

    try:
        lab.wait()
    except KeyboardInterrupt:
        print(
            "attempting to stop lab, you may want to check your process monitor",
            flush=True,
        )
    finally:
        stop()
        lab.terminate()
        lab.communicate(b"y\n")

    stop()
    lab.wait()
    return 0


if __name__ == "__main__":
    if "watch" in sys.argv:
        sys.exit(watch())
