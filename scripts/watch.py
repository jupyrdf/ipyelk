"""Watch all the things."""

from __future__ import annotations

import atexit
import subprocess
import sys
import time

WATCHES = [
    ["jlpm", "watch:lib"],
    ["jlpm", "watch:ext"],
]


def main() -> int:
    procs: list[subprocess.Popen] = []
    for cmd in WATCHES:
        print(">>>", *cmd)
        time.sleep(1)
        procs += [subprocess.Popen(cmd)]

    def stop():
        """Stop the processes."""
        for proc in procs:
            if proc.poll() is None:
                continue
            proc.terminate()
            proc.wait()

    atexit.register(stop)

    try:
        procs[0].wait()
    except KeyboardInterrupt:
        stop()

    return 1


if __name__ == "__main__":
    sys.exit(main())
