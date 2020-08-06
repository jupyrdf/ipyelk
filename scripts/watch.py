""" handle lingering issues with jupyterlab 1.x build
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

from jupyterlab.commands import get_app_dir

HERE = Path(__file__).parent
ROOT = HERE.parent

JLPM = shutil.which("jlpm")
APP_DIR = Path(get_app_dir())
STAGING = APP_DIR / "staging"
STATIC = APP_DIR / "static"
INDEX = STATIC / "index.html"

INTERVAL = 10


def prep():
    """ do a normal build of lab, then clean out static
    """
    subprocess.check_call([JLPM, "build"])
    subprocess.check_call(
        ["jupyter", "labextension", "install", ".", "--no-build", "--debug"],
        cwd=str(ROOT),
    )
    subprocess.check_call(["jupyter", "lab", "build"], cwd=str(ROOT))
    subprocess.check_call(
        [JLPM, "add", "--dev", "chokidar", "watchpack-chokidar2"], cwd=str(STAGING)
    )
    shutil.rmtree(STATIC)


def watch():
    """ after preparing, install missing dependencies, and start watchers
    """
    prep()
    ts = subprocess.Popen([JLPM, "watch"], cwd=str(ROOT))
    webpack = subprocess.Popen([JLPM, "watch"], cwd=str(STAGING))

    timeout = 120
    while timeout > 0 and not INDEX.exists():
        print(INDEX, f"not ready yet, will wait {timeout}s...")
        time.sleep(INTERVAL)
        timeout -= INTERVAL

    if timeout <= 0:
        print(INDEX, "not created, giving up!")
        ts.terminate()
        webpack.terminate()
        ts.wait()
        webpack.wait()
        return 1

    print("Built, starting lab...")

    lab = subprocess.Popen(
        ["jupyter", "lab", "--no-browser", "--debug"],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
    )

    try:
        lab.wait()
    except KeyboardInterrupt:
        print("attempting to stop lab, you may want to check your process monitor")
        lab.terminate()
        lab.communicate(b"y\n")
    finally:
        webpack.terminate()
        ts.terminate()

    lab.wait()
    ts.wait()
    webpack.wait()
    return 0


if __name__ == "__main__":
    sys.exit(watch())
