# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Dump every kernel thread's stack when a notebook cell wedges the kernel.

``nbconvert --execute`` gives up on a cell after ``ExecutePreprocessor.timeout``
seconds, but a kernel that never processes a request never prints anything, so
the job log shows the timeout and nothing else (#177).

This file runs as an IPython startup file in the kernels nbconvert launches
(``IPYTHONDIR`` is set by the ``nbconvert--`` task). ``faulthandler`` writes the
stacks from a watchdog thread without the GIL or the event loop, so a busy loop
cannot hide from it. The timer restarts whenever a cell starts, so it fires when
no cell has started for ``IPYELK_KERNEL_WATCHDOG`` seconds: a cell that runs that
long, or a request the kernel never got to. The task sets it to 30 s, under its
40 s cell timeout.

The dump goes to the kernel's real stderr, which nbconvert passes through to the
job log. On Linux and macOS, ipykernel has replaced file descriptor 2 with a pipe
that its ``_watch_pipe_fd`` thread forwards to IOPub. Writing there would wake
that thread mid-dump and make it look busy, so the dump uses ipykernel's own copy
of the original descriptor instead. Windows has no such pipe, and
``sys.__stderr__`` is the real stderr there.

A second, Python-level dump follows a second later: the pending ``asyncio`` tasks
of the kernel's event loops and whether the shell locks are held. It needs the
GIL, so if it never appears, something is likely holding the GIL. It is skipped
when the GIL is disabled, where walking another thread's coroutines is unsafe.
"""


def _ipyelk_asyncio_dumper():
    import asyncio
    import traceback

    max_tasks = 50

    def await_chain(coro):
        for _ in range(30):
            frame = getattr(coro, "cr_frame", getattr(coro, "gi_frame", None))
            if frame is not None:
                code = frame.f_code
                yield f"  {code.co_filename}:{frame.f_lineno} in {code.co_name}\n"
            coro = getattr(coro, "cr_await", getattr(coro, "gi_yieldfrom", None))
            if coro is None:
                return

    def dump_lock(out, name, lock):
        if lock is not None:
            waiters = len(getattr(lock, "_waiters", None) or ())
            out.write(f"{name}: locked={lock.locked()} waiters={waiters}\n")

    def dump_loop(out, name, owner):
        loop = getattr(getattr(owner, "io_loop", owner), "asyncio_loop", None)
        if loop is None:
            return
        tasks = list(asyncio.all_tasks(loop))
        out.write(f"\n{name}: {len(tasks)} pending task(s)\n")
        for task in tasks[:max_tasks]:
            out.write(f"{task!r}\n")
            out.writelines(await_chain(task.get_coro()))
        if len(tasks) > max_tasks:
            out.write(f"... {len(tasks) - max_tasks} more\n")

    def safely(dump, out, name, obj):
        try:
            dump(out, name, obj)
        except Exception:
            out.write(f"{name}: failed\n")
            traceback.print_exc(file=out)

    def dump_asyncio(fd, kernel):
        with open(fd, "w", encoding="utf-8", errors="replace", closefd=False) as out:
            out.write("\n--- ipyelk kernel watchdog: asyncio state ---\n")
            shell = getattr(kernel, "shell_channel_thread", None)
            sections = [
                (dump_lock, "shell lock", getattr(kernel, "_main_asyncio_lock", None)),
                (dump_lock, "shell channel lock", getattr(shell, "asyncio_lock", None)),
                (dump_loop, "io_loop", getattr(kernel, "io_loop", None)),
                (dump_loop, "shell_channel_thread", shell),
                (dump_loop, "control_thread", getattr(kernel, "control_thread", None)),
            ]
            for dump, name, obj in sections:
                safely(dump, out, name, obj)
            out.write("--- end asyncio state ---\n")

    return dump_asyncio


def _ipyelk_kernel_watchdog(dump_asyncio):
    import faulthandler
    import os
    import sys
    import threading

    from IPython import get_ipython

    timeout = float(os.environ.get("IPYELK_KERNEL_WATCHDOG", "900"))
    fd = getattr(sys.stderr, "_original_stdstream_copy", None)
    fd = os.dup(sys.__stderr__.fileno() if fd is None else fd)
    shell = get_ipython()
    kernel = getattr(shell, "kernel", None)
    with_asyncio = (
        kernel is not None and getattr(sys, "_is_gil_enabled", lambda: True)()
    )
    timers = []

    def arm(*_):
        # a new call replaces the pending dump
        faulthandler.dump_traceback_later(timeout, repeat=False, file=fd)
        if with_asyncio:
            for timer in timers:
                timer.cancel()
            timers[:] = [threading.Timer(timeout + 1, dump_asyncio, (fd, kernel))]
            timers[0].daemon = True
            timers[0].start()

    arm()
    if shell is not None:
        shell.events.register("pre_run_cell", arm)


_ipyelk_kernel_watchdog(_ipyelk_asyncio_dumper())
del _ipyelk_kernel_watchdog, _ipyelk_asyncio_dumper
