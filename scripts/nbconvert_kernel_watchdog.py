# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Dump every kernel thread's stack when a notebook cell wedges the kernel.

``nbconvert --execute`` gives up on a cell after ``ExecutePreprocessor.timeout``
seconds, but a kernel that never processes a request never prints anything, so
the job log shows the timeout and nothing else (#177).

This file runs as an IPython startup file in the kernels nbconvert launches
(``IPYTHONDIR`` is set by the ``nbconvert--`` task). ``faulthandler`` writes the
stacks from a watchdog thread without the GIL or the event loop, so a busy loop
cannot hide from it. The default of 900 s is under the 1200 s cell timeout and
far over any healthy run, and each notebook gets its own kernel, so the timer
starts fresh per notebook.

The dump goes to the kernel's real stderr, which nbconvert passes through to the
job log. On Linux and macOS, ipykernel has replaced file descriptor 2 with a pipe
that its ``_watch_pipe_fd`` thread forwards to IOPub. Writing there would wake
that thread mid-dump and make it look busy, so the dump uses ipykernel's own copy
of the original descriptor instead. Windows has no such pipe, and
``sys.__stderr__`` is the real stderr there.

A second, Python-level dump follows a second later: the pending ``asyncio`` tasks
of the kernel's event loops and whether the shell lock is held. It needs the GIL,
so if it never appears, something is holding the GIL.
"""


def _ipyelk_kernel_watchdog():
    import asyncio
    import faulthandler
    import os
    import sys
    import threading

    from IPython import get_ipython

    def await_chain(coro):
        for _ in range(30):
            frame = getattr(coro, "cr_frame", getattr(coro, "gi_frame", None))
            if frame is not None:
                code = frame.f_code
                yield f"  {code.co_filename}:{frame.f_lineno} in {code.co_name}\n"
            coro = getattr(coro, "cr_await", getattr(coro, "gi_yieldfrom", None))
            if coro is None:
                return

    def dump_loop(out, name, owner):
        loop = getattr(getattr(owner, "io_loop", owner), "asyncio_loop", None)
        if loop is None:
            return
        tasks = asyncio.all_tasks(loop)
        out.write(f"\n{name}: {len(tasks)} pending task(s)\n")
        for task in tasks:
            out.write(f"{task!r}\n")
            out.writelines(await_chain(task.get_coro()))

    def dump_asyncio(fd, kernel):
        with open(fd, "w", encoding="utf-8", errors="replace", closefd=False) as out:
            out.write("\n--- ipyelk kernel watchdog: asyncio state ---\n")
            lock = getattr(kernel, "_main_asyncio_lock", None)
            if lock is not None:
                waiters = len(getattr(lock, "_waiters", None) or ())
                out.write(f"shell lock: locked={lock.locked()} waiters={waiters}\n")
            for name in ["io_loop", "shell_channel_thread", "control_thread"]:
                dump_loop(out, name, getattr(kernel, name, None))
            out.write("--- end asyncio state ---\n")

    timeout = float(os.environ.get("IPYELK_KERNEL_WATCHDOG", "900"))
    fd = getattr(sys.stderr, "_original_stdstream_copy", None)
    fd = os.dup(sys.__stderr__.fileno() if fd is None else fd)
    faulthandler.dump_traceback_later(timeout, repeat=False, file=fd)
    kernel = getattr(get_ipython(), "kernel", None)
    if kernel is not None:
        timer = threading.Timer(timeout + 1, dump_asyncio, (fd, kernel))
        timer.daemon = True
        timer.start()


_ipyelk_kernel_watchdog()
del _ipyelk_kernel_watchdog
