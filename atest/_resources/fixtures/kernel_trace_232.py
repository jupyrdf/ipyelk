"""Trace ipykernel's shell dispatch and IOPub status publishes, for gh-232.

Loaded as an IPython startup file by the robot tests' kernels. Every line of the
trace is ``<epoch> <thread> <task> <event> ...``, written to
``<home>/kernel-trace/<pid>.log`` where ``<home>`` is the parent of ``IPYTHONDIR``.
The events:

- ``shell_main <subshell> <msg_type> <msg_id> <LOCKED|free> hdr_subshell=<id>``: a
  shell message reached a (sub)shell's loop; whether that shell's asyncio lock was
  already held; the subshell the client addressed in the header
- ``dispatch> <msg_type> <msg_id> [comm=<id>] <CONCURRENT|locked-path>`` and
  ``dispatch<``: ``Kernel.dispatch_shell`` entry and exit (ipykernel 7.4 dispatches
  comm messages concurrently, without busy/idle, when the lock is held)
- ``status <busy|idle> <channel> <parent msg_id> <parent msg_type>``: every
  IOPub status publish and the parent it carries

It never raises: a kernel that cannot trace still starts.
"""

import asyncio
import contextlib
import inspect
import os
import pathlib
import threading
import time

_STATE = {"trace": None}


def _task_id():
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return f"T{id(task) % 100000:05d}" if task else "T-----"


def _log(*parts):
    with contextlib.suppress(OSError, ValueError):
        _STATE["trace"].write(
            f"{time.time():.6f} {threading.current_thread().name} {_task_id()} "
            + " ".join(str(p) for p in parts)
            + "\n"
        )


def _message(kernel, msg):
    # ``content=False``: deserializing the content records the signature digest,
    # and the kernel's own deserialize would then reject the message as a replay
    try:
        _, frames = kernel.session.feed_identities(msg, copy=False)
        return kernel.session.deserialize(frames, content=False, copy=False)
    except Exception as err:  # the "stop aborting" dummy frames, for one
        return {"header": {"msg_type": f"?{type(err).__name__}", "msg_id": "?"}}


def _comm_of(kernel, msg):
    try:
        content = kernel.session.unpack(_message(kernel, msg)["content"])
        return str(content.get("comm_id", ""))[:8]
    except Exception:
        return "?"


def _subshell_lock(kernel, subshell_id):
    if subshell_id is None:
        return getattr(kernel, "_main_asyncio_lock", None)
    try:
        return kernel.shell_channel_thread.manager.get_subshell_asyncio_lock(
            subshell_id
        )
    except Exception:
        return None


def _install():
    import ipykernel
    import ipykernel.kernelbase as kb

    ipythondir = os.environ.get("IPYTHONDIR")
    if not ipythondir:
        return
    out = pathlib.Path(ipythondir).parent / "kernel-trace"
    out.mkdir(parents=True, exist_ok=True)
    _STATE["trace"] = (out / f"{os.getpid()}.log").open(
        "a", buffering=1, encoding="utf-8"
    )

    kernel_cls = kb.Kernel
    orig_shell_main = kernel_cls.shell_main
    orig_dispatch = kernel_cls.dispatch_shell
    orig_publish = kernel_cls._publish_status

    async def shell_main(self, subshell_id, msg):
        h = _message(self, msg)["header"]
        lock = _subshell_lock(self, subshell_id)
        _log(
            "shell_main",
            subshell_id,
            h.get("msg_type"),
            str(h.get("msg_id", ""))[:8],
            "LOCKED" if (lock is not None and lock.locked()) else "free",
            f"hdr_subshell={str(h.get('subshell_id'))[:8]}",
        )
        return await orig_shell_main(self, subshell_id, msg)

    async def dispatch_shell(self, msg, /, subshell_id=None, **kw):
        h = _message(self, msg)["header"]
        tag = f"{h.get('msg_type')} {str(h.get('msg_id', ''))[:8]}"
        if h.get("msg_type") in {"comm_msg", "comm_open", "comm_close"}:
            tag += f" comm={_comm_of(self, msg)}"
        _log("dispatch>", tag, "CONCURRENT" if kw.get("concurrent") else "locked-path")
        try:
            return await orig_dispatch(self, msg, subshell_id=subshell_id, **kw)
        finally:
            _log("dispatch<", tag)

    def _publish_status(self, status, channel, parent=None):
        try:
            p = parent or self.get_parent(channel) or {}
            ph = p.get("header", {}) if isinstance(p, dict) else {}
            _log(
                "status",
                status,
                channel,
                str(ph.get("msg_id", ""))[:8],
                ph.get("msg_type"),
            )
        except Exception:
            _log("status", status, channel, "?", "?")
        return orig_publish(self, status, channel, parent)

    kernel_cls.shell_main = shell_main
    kernel_cls.dispatch_shell = dispatch_shell
    kernel_cls._publish_status = _publish_status
    _log(
        "trace installed",
        f"ipykernel={ipykernel.__version__}",
        f"concurrent_kw={'concurrent' in inspect.signature(orig_dispatch).parameters}",
    )


try:
    _install()
except Exception as _err:  # diagnostics must not break kernels
    import sys

    print(f"kernel_trace_232: not installed: {_err!r}", file=sys.__stderr__)
finally:
    del _install
