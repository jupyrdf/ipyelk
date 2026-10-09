# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The test kernels' shell reply fix (#177).

Adapted from ipykernel's own regression test for the fix it shipped in 7.4
(``tests/test_subshell_wedge.py``, ipykernel#1529). A request is queued on the
shell ROUTER with its wake-up already consumed, as a raw send can do, then the
shell channel thread sends a reply. A raw send leaves the request stranded; a send
through the stream delivers it.
"""

import asyncio
import importlib.util
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

zmq = pytest.importorskip("zmq")
ipykernel = pytest.importorskip("ipykernel")
subshell_manager = pytest.importorskip("ipykernel.subshell_manager")
ipykernel_thread = pytest.importorskip("ipykernel.thread")
tornado_ioloop = pytest.importorskip("tornado.ioloop")
zmqstream = pytest.importorskip("zmq.eventloop.zmqstream")

SCRIPT = Path(__file__).parents[1] / "scripts" / "kernel_shell_reply_fix.py"
spec = importlib.util.spec_from_file_location("kernel_shell_reply_fix", SCRIPT)
assert spec
assert spec.loader
shell_reply_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell_reply_fix)

SubshellManager = subshell_manager.SubshellManager
# by version, so a broken ``fixed_upstream`` cannot skip the tests below
FIXED_UPSTREAM = ipykernel.version_info >= (7, 4)
NEEDS_FIX = pytest.mark.skipif(
    FIXED_UPSTREAM, reason="ipykernel sends through the stream"
)
TIMEOUT = 10.0

KERNEL_PROBE = """
from jupyter_client.manager import start_new_kernel

km, kc = start_new_kernel(startup_timeout=60)
code = (
    "import ipykernel\\n"
    "print(ipykernel.__version__)\\n"
    "manager = get_ipython().kernel.shell_channel_thread.manager\\n"
    "stream = manager._main_to_shell_channel.to_stream\\n"
    "print(stream._recv_callback.__qualname__)\\n"
    "print('_install' in globals())"
)
out = []
try:
    reply = kc.execute_interactive(
        code, timeout=30, output_hook=lambda m: out.append(m["content"].get("text", ""))
    )
    print(reply["content"]["status"], *"".join(out).split())
finally:
    kc.stop_channels()
    km.shutdown_kernel(now=True)
"""


class Opaque:
    """A fixture value with a short ``repr``.

    pytest formats test arguments on failure, and the pending futures of an
    ``IOLoop`` can take it minutes.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f"<{', '.join(self.__dict__)}>"


def run_on_loop(loop, func):
    """Run ``func()`` on ``loop``'s thread and return its result."""
    box = {}
    done = threading.Event()

    def runner():
        try:
            box["result"] = func()
        except BaseException as err:
            box["error"] = err
        finally:
            done.set()

    loop.add_callback(runner)
    assert done.wait(TIMEOUT), "callback did not run on the shell channel loop"
    if "error" in box:
        raise box["error"]
    return box.get("result")


@pytest.fixture
def shell_channel_loop():
    """An ``IOLoop`` on a thread named like ipykernel's shell channel thread."""
    box = {}
    ready = threading.Event()

    def run():
        asyncio.set_event_loop(asyncio.new_event_loop())
        box["loop"] = loop = tornado_ioloop.IOLoop.current()
        loop.add_callback(ready.set)
        loop.start()

    name = ipykernel_thread.SHELL_CHANNEL_THREAD_NAME
    thread = threading.Thread(target=run, name=name, daemon=True)
    thread.start()
    assert ready.wait(TIMEOUT)
    yield Opaque(loop=box["loop"])
    box["loop"].add_callback(box["loop"].stop)
    thread.join(TIMEOUT)


@pytest.fixture
def sockets():
    """A shell ROUTER and a client DEALER connected to it."""
    context = zmq.Context()
    shell_socket = context.socket(zmq.ROUTER)
    port = shell_socket.bind_to_random_port("tcp://127.0.0.1")
    client = context.socket(zmq.DEALER)
    client.setsockopt(zmq.IDENTITY, b"client")
    client.connect(f"tcp://127.0.0.1:{port}")
    yield Opaque(context=context, shell_socket=shell_socket, client=client)
    # closes every socket first, so one left open cannot block it
    context.destroy(linger=0)


def test_no_op_when_fixed_upstream():
    class Manager(SubshellManager):
        pass

    assert shell_reply_fix.fixed_upstream(SubshellManager) is FIXED_UPSTREAM
    patched = shell_reply_fix.patch_send_on_shell_channel(Manager, None)
    assert patched is not FIXED_UPSTREAM
    if FIXED_UPSTREAM:
        assert "_send_on_shell_channel" not in vars(Manager)


@NEEDS_FIX
@pytest.mark.parametrize(
    "fixed",
    [
        True,
        pytest.param(
            False,
            marks=pytest.mark.skipif(
                sys.platform == "win32",
                reason="this harness does not strand the request on Windows",
            ),
        ),
    ],
)
def test_reply_send_does_not_strand_a_request(shell_channel_loop, sockets, fixed):
    loop = shell_channel_loop.loop
    shell_socket, client = sockets.shell_socket, sockets.client
    received = []
    got = threading.Event()

    class Manager(SubshellManager):
        pass

    def on_recv(frames):
        received.append(frames)
        got.set()

    def setup():
        stream = zmqstream.ZMQStream(shell_socket, loop)
        stream.on_recv(on_recv, copy=True)
        if fixed:
            assert shell_reply_fix.patch_send_on_shell_channel(Manager, stream)
        return stream, Manager(sockets.context, loop, shell_socket)

    def strand_then_reply():
        # on the loop thread, so the stream cannot read in between
        client.send_multipart([b"request"])
        deadline = time.monotonic() + TIMEOUT
        # reading EVENTS consumes the wake-up, as a raw send would
        while not shell_socket.events & zmq.POLLIN:
            assert time.monotonic() < deadline, "request never queued"
        assert not got.is_set()
        manager._send_on_shell_channel([b"client", b"reply"])

    def teardown():
        manager.close()
        stream.close()

    stream, manager = run_on_loop(loop, setup)
    try:
        client.send_multipart([b"warmup"])
        assert got.wait(TIMEOUT), "warmup request never delivered"
        got.clear()
        run_on_loop(loop, strand_then_reply)
        if fixed:
            assert got.wait(TIMEOUT), "the request was stranded by the reply send"
            assert received[-1][-1] == b"request"
            assert client.poll(int(TIMEOUT * 1000))
            assert client.recv_multipart() == [b"reply"]
        else:
            # the ipykernel 7.0 to 7.3 behavior the fix exists for
            assert not got.wait(1.0)
    finally:
        run_on_loop(loop, teardown)


@NEEDS_FIX
def test_startup_file_patches_the_kernel(tmp_path):
    pytest.importorskip("jupyter_client.manager")
    startup = tmp_path / "profile_default" / "startup"
    startup.mkdir(parents=True)
    (startup / "00-shell-reply-fix.py").write_text(SCRIPT.read_text(encoding="utf-8"))
    env = {**os.environ, "IPYTHONDIR": str(tmp_path)}
    # in a child process, so a kernel that never answers fails the test, not the job
    proc = subprocess.run(
        [sys.executable, "-c", KERNEL_PROBE],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    # a user kernel spec could start another environment's kernel
    assert proc.stdout.split()[-4:] == [
        "ok",
        ipykernel.__version__,
        "patch_send_on_shell_channel.<locals>._send_on_shell_channel",
        "False",
    ], proc.stderr
