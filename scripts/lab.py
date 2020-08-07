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


def build(args=None):
    args = (
        args if args is not None else ["--debug", "--minimize=True", "--devBuild=False"]
    )
    subprocess.check_call(["jupyter", "lab", "build"], cwd=str(ROOT))
    return 0


def prep():
    """ do a normal build of lab, then clean out static
    """
    print("building extension...", flush=True)
    subprocess.check_call([JLPM, "build"])
    print("installing extension...", flush=True)
    subprocess.check_call(
        ["jupyter", "labextension", "link", ".", "--no-build", "--debug"],
        cwd=str(ROOT),
    )
    print("pre-building lab...", flush=True)
    build(["--debug"])
    print("adding missing deps...", flush=True)
    subprocess.check_call(
        [JLPM, "add", "--dev", "chokidar", "watchpack-chokidar2", "--ignore-optional"],
        cwd=str(STAGING),
    )
    print("cleaning lab...", flush=True)
    shutil.rmtree(STATIC)


def watch():
    """ after preparing, install missing dependencies, and start watchers
    """
    prep()
    print("watching src...", flush=True)
    ts = subprocess.Popen([JLPM, "watch"], cwd=str(ROOT))
    print("watching webpack...", flush=True)
    webpack = subprocess.Popen([JLPM, "watch"], cwd=str(STAGING))

    def stop():
        print("stopping watchers...", flush=True)
        ts.terminate()
        webpack.terminate()
        ts.wait()
        webpack.wait()
        print("...watchers stopped!", flush=True)

    timeout = 120
    while timeout > 0 and not INDEX.exists():
        print(f"Lab not ready yet, will wait {timeout}s...", flush=True)
        time.sleep(INTERVAL)
        timeout -= INTERVAL

    if timeout <= 0:
        print(INDEX, "not created, giving up!", flush=True)
        stop()
        return 1

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
    if "build" in sys.argv:
        sys.exit(build())
    if "watch" in sys.argv:
        sys.exit(watch())
