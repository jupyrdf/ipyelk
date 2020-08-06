""" handle lingering issues with jupyterlab 1.x build
"""

import atexit
import shutil
import subprocess
import sys
import time
from logging import getLogger
from pathlib import Path

from jupyterlab.commands import get_app_dir

log = getLogger(__name__)


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
    log.warning("building extension...")
    subprocess.check_call([JLPM, "build"])
    log.warning("installing extension...")
    subprocess.check_call(
        ["jupyter", "labextension", "install", ".", "--no-build", "--debug"],
        cwd=str(ROOT),
    )
    log.warning("pre-building lab...")
    subprocess.check_call(
        ["jupyter", "lab", "build", "--minimize=False"], cwd=str(ROOT)
    )
    log.warning("adding missing deps...")
    subprocess.check_call(
        [JLPM, "add", "--dev", "chokidar", "watchpack-chokidar2", "--ignore-optional"],
        cwd=str(STAGING),
    )
    log.warning("cleaning lab...")
    shutil.rmtree(STATIC)


def watch():
    """ after preparing, install missing dependencies, and start watchers
    """
    prep()
    log.warning("watching src...")
    ts = subprocess.Popen([JLPM, "watch"], cwd=str(ROOT))
    log.warning("watching webpack...")
    webpack = subprocess.Popen([JLPM, "watch"], cwd=str(STAGING))

    lab = None

    def stop():
        if lab is not None and lab.returncode is not None:
            try:
                log.warning(
                    "Stopping lab, you may want to check your process monitor..."
                )
                lab.terminate()
                lab.communicate(b"y\n")
                lab.wait()
            except:
                pass
        log.warning("stopping watchers...")
        ts.terminate()
        webpack.terminate()
        ts.wait()
        webpack.wait()
        log.warning("...watchers stopped!")

    atext.register(stop)

    timeout = 300
    while wepack.returncode is None and timeout > 0 and not INDEX.exists():
        log.warning(f"Lab not ready yet, will wait {timeout}s...")
        time.sleep(INTERVAL)
        timeout -= INTERVAL

    if wepack.returncode is not None or timeout <= 0:
        log.warning(INDEX, "not created, giving up!")
        stop()
        return 1

    log.warning("Initial build complete, starting lab...")

    lab = subprocess.Popen(
        ["jupyter", "lab", "--no-browser", "--debug"],
        cwd=str(ROOT),
        stdin=subprocess.PIPE,
    )

    try:
        lab.wait()
    except (Exception, KeyboardInterrupt):
        stop()

    return 0


if __name__ == "__main__":
    sys.exit(watch())
