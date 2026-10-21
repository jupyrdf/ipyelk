"""Trace ipykernel's shell dispatch and IOPub status publishes, for gh-232.

Loaded as an IPython startup file by the robot tests' kernels. Every line of the
trace is ``<epoch> <thread> <task> <event> ...``, written to
``<home>/kernel-trace/<pid>.log`` where ``<home>`` is the parent of ``IPYTHONDIR``.
The events:

- ``shell_main <subshell> <msg_type> <msg_id> <LOCKED|free>``: a shell message
  reached the subshell's loop; whether its asyncio lock was already held
- ``dispatch> <msg_type> <msg_id> <CONCURRENT|locked-path>`` and ``dispatch<``:
  ``Kernel.dispatch_shell`` entry and exit (ipykernel 7.4 dispatches comm
  messages concurrently, without busy/idle, when the lock is held)
- ``status <busy|idle> <channel> <parent msg_id> <parent msg_type>``: every
  IOPub status publish and the parent it carries

It never raises: a kernel that cannot trace still starts.
"""

import asyncio
import inspect
import os
import pathlib
import threading
import time


def _install():
    import ipykernel.kernelbase as kb

    ipythondir = os.environ.get("IPYTHONDIR")
    if not ipythondir:
        return
    out = pathlib.Path(ipythondir).parent / "kernel-trace"
    out.mkdir(parents=True, exist_ok=True)
    trace = open(out / f"{os.getpid()}.log", "a", buffering=1)  # noqa: SIM115

    def task_id():
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        return f"T{id(task) % 100000:05d}" if task else "T-----"

    def log(*parts):
        try:
            trace.write(
                f"{time.time():.6f} {threading.current_thread().name} {task_id()} "
                + " ".join(str(p) for p in parts)
                + "\n"
            )
        except Exception:
            pass

    def header(kernel, msg):
        try:
            _, frames = kernel.session.feed_identities(msg, copy=False)
            return kernel.session.deserialize(frames, content=False, copy=False)["header"]
        except Exception as err:  # the "stop aborting" dummy frames, for one
            return {"msg_type": f"?{type(err).__name__}", "msg_id": "?"}

    kernel_cls = kb.Kernel
    orig_shell_main = kernel_cls.shell_main
    orig_dispatch = kernel_cls.dispatch_shell
    orig_publish = kernel_cls._publish_status

    async def shell_main(self, subshell_id, msg):
        h = header(self, msg)
        lock = getattr(self, "_main_asyncio_lock", None) if subshell_id is None else None
        log(
            "shell_main",
            subshell_id,
            h.get("msg_type"),
            str(h.get("msg_id", ""))[:8],
            "LOCKED" if (lock is not None and lock.locked()) else "free",
        )
        return await orig_shell_main(self, subshell_id, msg)

    async def dispatch_shell(self, msg, /, subshell_id=None, **kw):
        h = header(self, msg)
        tag = f"{h.get('msg_type')} {str(h.get('msg_id', ''))[:8]}"
        log("dispatch>", tag, "CONCURRENT" if kw.get("concurrent") else "locked-path")
        try:
            return await orig_dispatch(self, msg, subshell_id=subshell_id, **kw)
        finally:
            log("dispatch<", tag)

    def _publish_status(self, status, channel, parent=None):
        try:
            p = parent or self.get_parent(channel) or {}
            ph = p.get("header", {}) if isinstance(p, dict) else {}
            log("status", status, channel, str(ph.get("msg_id", ""))[:8], ph.get("msg_type"))
        except Exception:
            log("status", status, channel, "?", "?")
        return orig_publish(self, status, channel, parent)

    kernel_cls.shell_main = shell_main
    kernel_cls.dispatch_shell = dispatch_shell
    kernel_cls._publish_status = _publish_status
    import ipykernel

    log(
        "trace installed",
        f"ipykernel={ipykernel.__version__}",
        f"concurrent_kw={'concurrent' in inspect.signature(orig_dispatch).parameters}",
    )


try:
    _install()
except Exception as _err:  # pragma: no cover - diagnostics must not break kernels
    import sys

    print(f"kernel_trace_232: not installed: {_err!r}", file=sys.__stderr__)
finally:
    del _install
