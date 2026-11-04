# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""The test kernels' comm subshell routing fix (#232).

ipykernel 7.4 dispatches a comm message on the (sub)shell the kernel last sent on
that comm from, not on the one the client addressed. With JupyterLab 4.6 sending
widget messages on a subshell, two widgets' updates then run on two threads at
once, and ipywidgets' ``interact`` leaks the inner one's ``status: idle`` past the
page's Output hook, which wedges that widget's message throttle.

The kernel test plays the page: a subshell, two sliders of one ``interact`` whose
function is slow for one call, the first update of ``b`` to prime the routing,
then an update of ``a`` (slow) and one of ``b`` back to back. Without the fix,
``a`` runs on the main thread, ``b`` on the subshell, and ``b``'s idle is
published before any ``msg_id`` reset. With it, both run on the subshell, in
order, each idle after its reset.
"""

import importlib.util
import json
import os
import runpy
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ipykernel = pytest.importorskip("ipykernel")

SCRIPT = Path(__file__).parents[1] / "scripts" / "kernel_comm_subshell_fix.py"
spec = importlib.util.spec_from_file_location("kernel_comm_subshell_fix", SCRIPT)
assert spec
assert spec.loader
comm_subshell_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comm_subshell_fix)

# by version, so a broken ``routes_by_last_send`` cannot skip the tests below
ROUTES_BY_LAST_SEND = ipykernel.version_info >= (7, 4)
NEEDS_FIX = pytest.mark.skipif(
    not ROUTES_BY_LAST_SEND, reason="ipykernel dispatches where the client addressed"
)

KERNEL_PROBE = """
import json, sys, time
from jupyter_client.manager import start_new_kernel

km, kc = start_new_kernel(startup_timeout=60)
try:
    req = kc.session.msg("create_subshell_request", {})
    kc.control_channel.send(req)
    while True:
        reply = kc.get_control_msg(timeout=30)
        if reply["parent_header"].get("msg_id") == req["header"]["msg_id"]:
            subshell = reply["content"]["subshell_id"]
            break
    setup_id = kc.execute(
        "import ipywidgets as W, threading, time\\n"
        "calls = []\\n"
        "@W.interact(a=W.IntSlider(0, 0, 9, continuous_update=False),"
        " b=W.IntSlider(0, 0, 9, continuous_update=False))\\n"
        "def f(a, b):\\n"
        "    calls.append((a, b, threading.current_thread().name))\\n"
        "    if (a, b) == (1, 1):\\n"
        "        print('slow call started', flush=True)\\n"
        "        time.sleep(0.5)  # keeps its `with out:` open\\n"
    )

    def until(predicate):
        out, deadline = [], time.monotonic() + 30
        while time.monotonic() < deadline:
            m = kc.get_iopub_msg(timeout=30)
            out.append(m)
            if predicate(m):
                return out
        raise TimeoutError("IOPub event did not arrive")

    def idle(msg_id):
        return lambda m: (m["parent_header"].get("msg_id") == msg_id
                          and m["msg_type"] == "status"
                          and m["content"]["execution_state"] == "idle")

    msgs = until(idle(setup_id))
    a, b = [
        m["content"]["comm_id"]
        for m in msgs
        if m["msg_type"] == "comm_open"
        and m["content"]["data"].get("state", {}).get("_model_name") == "IntSliderModel"
    ][:2]

    def send(comm_id, value):
        msg = kc.session.msg(
            "comm_msg",
            {"comm_id": comm_id, "data": {"method": "update", "state": {"value": value}, "buffer_paths": []}},
        )
        msg["header"]["subshell_id"] = subshell  # as JupyterLab 4.6 addresses widget comms
        kc.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def events(msgs, ids):
        # per message, and in IOPub order: its status, and the Output's captured msg_id
        out = {tag: [] for tag in ids}
        order = []
        for m in msgs:
            tag = next((k for k, v in ids.items() if v == m["parent_header"].get("msg_id")), None)
            if tag is None:
                continue
            if m["msg_type"] == "status":
                event = "status " + m["content"]["execution_state"]
            elif m["msg_type"] == "comm_msg" and "msg_id" in m["content"]["data"].get("state", {}):
                captured = m["content"]["data"]["state"]["msg_id"]
                event = "out.msg_id = " + next((k for k, v in ids.items() if v == captured), "''")
            else:
                continue
            out[tag].append(event)
            order.append(f"{tag}: {event}")
        out["order"] = order
        return out

    # prime b: its first update runs on the main shell and its echo records the subshell
    prime = send(b, 1)
    until(idle(prime))
    ids = {"a1": send(a, 1)}
    msgs = until(lambda m: m["msg_type"] == "stream"
                 and "slow call started" in m["content"]["text"])
    ids["b1"] = send(b, 2)
    pending = set(ids.values())
    def both_idle(m):
        if m["msg_type"] == "status" and m["content"]["execution_state"] == "idle":
            pending.discard(m["parent_header"].get("msg_id"))
        return not pending
    msgs += until(both_idle)
    result = {"events": events(msgs, ids)}
    read_id = kc.execute("import json; print(json.dumps(calls))")
    for m in until(idle(read_id)):
        if m["msg_type"] == "stream" and m["content"]["text"].startswith("[["):
            result["threads"] = {f"{a}{b}": t for a, b, t in json.loads(m["content"]["text"])}
    print(json.dumps(result))
finally:
    kc.stop_channels()
    km.shutdown_kernel(now=True)
"""


class FakeComm:
    """What ``patch_reply_subshell_for`` needs of an ipykernel 7.4 comm."""

    def __init__(self):
        self._reply_subshell_lock = threading.Lock()
        self._reply_subshell_ids = {"request-1": "subshell-of-the-request"}
        self._reply_subshell_id = "subshell-of-the-last-send"

    def _reply_subshell_for(self, data, default):
        return self._reply_subshell_id


def test_no_op_without_last_send_routing():
    class Comm:
        pass

    assert comm_subshell_fix.routes_by_last_send(Comm) is False
    assert comm_subshell_fix.patch_reply_subshell_for(Comm) is False
    assert "_reply_subshell_for" not in vars(Comm)


@NEEDS_FIX
def test_patch_keeps_request_routing_and_honors_the_client():
    class Comm(FakeComm):
        pass

    assert comm_subshell_fix.routes_by_last_send(Comm) is True
    assert comm_subshell_fix.patch_reply_subshell_for(Comm) is True
    comm = Comm()
    request = {"method": "custom", "content": {"id": "request-1", "value": 42}}
    assert comm._reply_subshell_for(request, "addressed") == "subshell-of-the-request"
    assert comm._reply_subshell_ids == {}
    assert comm._reply_subshell_for(request, "addressed") == "addressed"
    assert comm._reply_subshell_for({"content": {"id": 42}}, "addressed") == "addressed"
    update = {"method": "update", "state": {"value": 1}, "buffer_paths": []}
    assert comm._reply_subshell_for(update, "addressed") == "addressed"
    assert comm._reply_subshell_for(update, None) is None


@NEEDS_FIX
def test_patch_is_harmless_without_the_routing_state():
    class Comm:
        def _reply_subshell_for(self, data, default):
            return "subshell-of-the-last-send"

    class LockOnly(Comm):
        _reply_subshell_lock = threading.Lock()

    assert comm_subshell_fix.patch_reply_subshell_for(Comm) is True
    assert comm_subshell_fix.patch_reply_subshell_for(LockOnly) is True
    request = {"method": "custom", "content": {"id": "request-1"}}
    # no lock or no reply table: dispatch where the client addressed, do not raise
    assert Comm()._reply_subshell_for(request, "addressed") == "addressed"
    assert LockOnly()._reply_subshell_for(request, "addressed") == "addressed"


def run_kernel_probe(tmp_path, fixed):
    pytest.importorskip("jupyter_client.manager")
    pytest.importorskip("ipywidgets")
    startup = tmp_path / "profile_default" / "startup"
    startup.mkdir(parents=True)
    if fixed:
        (startup / "00-comm-subshell-fix.py").write_text(
            SCRIPT.read_text(encoding="utf-8")
        )
    env = {**os.environ, "IPYTHONDIR": str(tmp_path), "JUPYTER_PLATFORM_DIRS": "1"}
    # in a child process, so a kernel that never answers fails the test, not the job;
    # files, not pipes: on Windows a timeout waits for every pipe to close, and the
    # kernel inherits them
    out, err = tmp_path / "stdout.txt", tmp_path / "stderr.txt"
    with out.open("w") as stdout, err.open("w") as stderr:
        proc = subprocess.run(
            [sys.executable, "-c", KERNEL_PROBE],
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=180,
            check=False,
        )
    errors = err.read_text(errors="replace")
    assert proc.returncode == 0, errors
    result = json.loads(out.read_text().strip().splitlines()[-1])
    # calls are keyed by their (a, b) values: a1 is the (1, 1) call, b1 the (1, 2) one
    return (
        result["events"],
        {"a1": result["threads"]["11"], "b1": result["threads"]["12"]},
        errors,
    )


@NEEDS_FIX
def test_kernel_dispatches_where_the_client_addressed(tmp_path):
    events, threads, errors = run_kernel_probe(tmp_path, fixed=True)
    for tag in ("a1", "b1"):
        assert threads[tag].startswith("subshell-"), (tag, threads, events, errors)
        assert events[tag].index("out.msg_id = ''") < events[tag].index(
            "status idle"
        ), (
            tag,
            events,
            errors,
        )
    assert events["b1"][0] == "status busy"


@NEEDS_FIX
def test_kernel_without_the_fix_leaks_the_inner_idle(tmp_path):
    """The ipykernel 7.4 behavior the fix exists for.

    If this fails after an ipykernel upgrade, ipykernel may dispatch where the client
    addressed again, and ``scripts/kernel_comm_subshell_fix.py`` may be obsolete.
    """
    events, threads, errors = run_kernel_probe(tmp_path, fixed=False)
    assert threads["a1"] == "MainThread", (threads, events, errors)
    assert threads["b1"].startswith("subshell-"), (threads, events, errors)
    # the idle of `b` goes out while the Output's last published msg_id, the page's
    # hook target, is still that of `b`: whichever message published it
    order = events["order"]
    before_idle = order[: order.index("b1: status idle")]
    captures = [e for e in before_idle if "out.msg_id" in e]
    assert captures[-1] == "b1: out.msg_id = b1", (order, errors)


ASYNC_PROBE = """
import json
from jupyter_client.manager import start_new_kernel

km, kc = start_new_kernel(startup_timeout=60)
try:
    def collect(msg_id):
        out = []
        while True:
            m = kc.get_iopub_msg(timeout=30)
            out.append(m)
            if (m["parent_header"].get("msg_id") == msg_id
                and m["msg_type"] == "status"
                and m["content"]["execution_state"] == "idle"):
                return out

    req = kc.session.msg("create_subshell_request", {})
    kc.control_channel.send(req)
    while True:
        reply = kc.get_control_msg(timeout=30)
        if reply["parent_header"].get("msg_id") == req["header"]["msg_id"]:
            subshell = reply["content"]["subshell_id"]
            break
    msgs = collect(kc.execute(
        "import asyncio, threading, ipywidgets as W; slider = W.IntSlider(); display(slider)"
    ))
    comm_id = next(m["content"]["comm_id"] for m in msgs
                   if m["msg_type"] == "comm_open"
                   and m["content"]["data"].get("state", {}).get("_model_name") == "IntSliderModel")
    cell = kc.execute("print('awaiting', flush=True); await asyncio.sleep(1)")
    while True:
        m = kc.get_iopub_msg(timeout=30)
        if m["msg_type"] == "stream" and "awaiting" in m["content"]["text"]:
            break
    msg = kc.session.msg("comm_msg", {"comm_id": comm_id, "data": {
        "method": "update", "state": {"value": 1}, "buffer_paths": []}})
    if ADDRESSED:
        msg["header"]["subshell_id"] = subshell
    kc.shell_channel.send(msg)
    msgs = collect(cell)
    # A barrier on the addressed subshell ensures all its messages have finished.
    barrier = kc.session.msg("execute_request", {"code": "pass", "silent": True,
        "store_history": False, "user_expressions": {}, "allow_stdin": False,
        "stop_on_error": True})
    barrier["header"]["subshell_id"] = subshell
    kc.shell_channel.send(barrier)
    msgs += collect(barrier["header"]["msg_id"])
    status = [m["content"]["execution_state"] for m in msgs
              if m["parent_header"].get("msg_id") == msg["header"]["msg_id"]
              and m["msg_type"] == "status"]
    msgs = collect(kc.execute("print('value:', slider.value)"))
    assert any('value: 1' in m["content"].get("text", "") for m in msgs), msgs
    print(json.dumps(status))
finally:
    kc.stop_channels()
    km.shutdown_kernel(now=True)
"""


@NEEDS_FIX
@pytest.mark.parametrize(
    ("fixed", "addressed", "expected"),
    [
        (False, True, []),
        (False, False, []),
        (True, True, ["busy", "idle"]),
    ],
)
def test_async_cell_comm_status(tmp_path, fixed, addressed, expected):
    """Canary: disabling subshell addressing alone cannot fix concurrent dispatch.

    When stock ipykernel supplies status here, revalidate the workaround upstream.
    """
    startup = tmp_path / "profile_default" / "startup"
    startup.mkdir(parents=True)
    if fixed:
        (startup / "00-comm-subshell-fix.py").write_text(SCRIPT.read_text())
    env = {**os.environ, "IPYTHONDIR": str(tmp_path), "JUPYTER_PLATFORM_DIRS": "1"}
    result = subprocess.run(
        [sys.executable, "-c", f"ADDRESSED = {addressed!r}\n" + ASYNC_PROBE],
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1]) == expected, result.stderr


def test_startup_cleans_its_namespace():
    namespace = runpy.run_path(str(SCRIPT), run_name="__main__")
    assert (
        not {
            "_install",
            "patch_reply_subshell_for",
            "request_id_of",
            "routes_by_last_send",
        }
        & namespace.keys()
    )


@pytest.mark.parametrize(
    ("version", "warning"), [((7, 3, 0), False), ((7, 5, 0), True)]
)
def test_install_does_not_patch_other_versions(monkeypatch, capsys, version, warning):
    monkeypatch.setattr(ipykernel, "version_info", version)
    patched = []
    monkeypatch.setattr(comm_subshell_fix, "patch_reply_subshell_for", patched.append)
    # sys.__stderr__ intentionally bypasses IPython capture in a real kernel.
    monkeypatch.setattr(sys, "__stderr__", sys.stderr)
    comm_subshell_fix._install()
    assert not patched
    assert ("not applied" in capsys.readouterr().err) is warning
