# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Headless benchmark of ``Diagram.refresh`` (kernel side + real elkjs in node).

    pixi run -e utest python scripts/bench_pipeline.py --label master

Writes ``build/bench/<label>.json`` and prints a markdown table, so a pipeline
change can be shown to beat the recorded 2.1.x baseline (jupyrdf/ipyelk#161,
#164).

Real: every kernel-side cost (pydantic dump/rebuild, ``persist`` merges,
``ValidationPipe``, ``VisibilityPipe``, ipywidgets state walks, echoes, the
property-lock compare, ``Diagram.refresh`` and its done-callback) and the ELK
layout itself (``elk.bundled.js`` in node -- the engine the browser worker
runs, with the same property stripping ``js/layout_widget_util.ts`` does).

Stubbed: the two browser stages. The text sizer assigns a fixed width per
character; the layout stage hands the projection to node. Both send the same
``{"action": "run"}`` custom message the real pipes send and feed the answer
back through the REAL browser->kernel path (``json.loads`` +
``Widget.set_state``), so echoes and pydantic rebuilds happen as in a kernel.

Not measurable here: DOM text measurement, sprotty rendering, browser
``JSON.parse``, transport latency, and -- by default -- the ``browser_roundtrip``
resend loop (the stub answers the first request, so ``runs`` is a lower bound).
``--slow-browser SECONDS`` instead routes the layout stage through the real
``ElkJS.run`` and answers each ``run`` request after that delay, with the
frontend's in-flight/queue semantics (``js/layout_widget_util.ts``
``RunQueue``): a delay past the resend interval (0.5 s) shows how many
layouts the browser performs per refresh (``Layouts`` column).


Pipe times exclude the sync work their own outlet assignment triggers, so pipe
time and "kernel sync" do not double-count.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

os.environ.setdefault("IPYELK_NO_BROWSER", "1")
os.environ.setdefault("IPYELK_TESTING", "1")

SIZES = (100, 500, 1000)
SHAPES = ("flat", "nested")
SEED = 0
HIDDEN_FRACTION = 0.07
BURST = 10
CHAR_WIDTH = 8.0
LINE_HEIGHT = 14.0

#: disjoint leaf timers that together make up "kernel sync work"
SYNC_LABELS = (
    "to_json (pydantic dump)",
    "from_json (convert_elkjson rebuild)",
    "persist (index merge)",
    "json.dumps (comm out)",
    "json.loads (comm in)",
    "ipywidgets _remove_buffers",
    "ipywidgets lock-compare json",
)

NODE_SCRIPT = r"""
const fs = require('fs'), readline = require('readline');
const { performance } = require('perf_hooks');
const elk = new (require(process.env.IPYELK_BENCH_ELKJS))();
// mirrors js/layout_widget_util.ts collectProperties / applyProperties
function walk(n, fn) {
  fn(n);
  for (const k of ['children', 'ports', 'labels', 'edges'])
    for (const c of n[k] || []) walk(c, fn);
}
let chain = Promise.resolve();
readline.createInterface({ input: process.stdin }).on('line', (line) => {
  const path = line.trim();
  if (!path) return;
  chain = chain.then(async () => {
    try {
      const t0 = performance.now();
      const graph = JSON.parse(fs.readFileSync(path, 'utf8'));
      const props = {};
      walk(graph, (n) => { props[n.id] = n.properties; delete n.properties; });
      const t1 = performance.now();
      const result = await elk.layout(graph);
      const t2 = performance.now();
      walk(result, (n) => { n.properties = props[n.id]; });
      fs.writeFileSync(path + '.out.json', JSON.stringify(result));
      process.stdout.write(JSON.stringify({ ok: true, ms_layout: t2 - t1,
        ms_other: t1 - t0 + performance.now() - t2 }) + '\n');
    } catch (err) {
      process.stdout.write(JSON.stringify({ ok: false, error: String(err) }) + '\n');
    }
  });
}).on('close', () => chain.then(() => process.exit(0)));
"""

PROF: dict[str, float] = defaultdict(float)
CALLS: dict[str, int] = defaultdict(int)


@contextmanager
def timed(label: str):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        PROF[label] += time.perf_counter() - t0
        CALLS[label] += 1


@contextmanager
def timed_pipe(label: str):
    """Time a pipe, and also net of the sync work its outlet assignment causes."""
    before = sync_total()
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        PROF[label] += elapsed
        PROF[f"{label} (excl sync)"] += elapsed - (sync_total() - before)
        CALLS[label] += 1


def sync_total() -> float:
    return sum(PROF[label] for label in SYNC_LABELS)


class Recorder:
    """Records every kernel -> browser comm message and the browser's copy."""

    def __init__(self) -> None:
        self.log: list[dict] = []
        self.roles: dict[str, str] = {}
        self.last_state: dict[str, dict] = {}
        self.enabled = False
        self.inbound = [0, 0]  # messages, bytes

    def record(self, comm_id: str, data: dict | None) -> None:
        data = data or {}
        state = data.get("state") or {}
        if state:
            self.last_state.setdefault(comm_id, {}).update(state)
        if not self.enabled:
            return
        with timed("json.dumps (comm out)"):
            nbytes = len(json.dumps(data))
        self.log.append({
            "widget": self.roles.get(comm_id, "?"),
            "method": data.get("method", "open"),
            "action": (data.get("content") or {}).get("action"),
            "keys": ",".join(sorted(state)),
            "bytes": nbytes,
        })

    def value_of(self, widget) -> dict:
        """What the frontend model holds for this widget's ``value``."""
        return self.last_state.get(widget.comm.comm_id, {}).get("value")

    def summarize(self, start: int, since: tuple[int, int] = (0, 0)) -> dict:
        messages: dict[str, int] = defaultdict(int)
        nbytes: dict[str, int] = defaultdict(int)
        runs: dict[str, int] = defaultdict(int)
        rows: dict[tuple, dict] = {}
        for msg in self.log[start:]:
            messages[msg["method"]] += 1
            nbytes[msg["method"]] += msg["bytes"]
            if msg["action"] == "run":
                runs[msg["widget"]] += 1
            row = rows.setdefault(
                (msg["widget"], msg["method"], msg["keys"]), {"count": 0, "bytes": 0}
            )
            row["count"] += 1
            row["bytes"] += msg["bytes"]
        return {
            "messages": {**messages, "total": sum(messages.values())},
            "bytes": {**nbytes, "total": sum(nbytes.values())},
            "runs": dict(runs),
            "browser_to_kernel": {
                "messages": self.inbound[0] - since[0],
                "bytes": self.inbound[1] - since[1],
            },
            "rows": [
                {"widget": k[0], "method": k[1], "keys": k[2], **v}
                for k, v in sorted(rows.items(), key=lambda kv: -kv[1]["bytes"])
            ],
        }


RECORDER = Recorder()


class RecordingComm:
    """Stand-in for ipykernel's Comm (see ipywidgets ``Widget.open``/``_send``)."""

    def __init__(self, data=None, comm_id=None, **kwargs) -> None:
        self.comm_id = comm_id or uuid.uuid4().hex
        self.kernel = object()  # non-None, so Widget._send actually sends
        RECORDER.record(self.comm_id, data)

    def send(self, data=None, metadata=None, buffers=None, **kwargs) -> None:
        RECORDER.record(self.comm_id, data)
        content = (data or {}).get("content") or {}
        if BROWSER is not None and content.get("action") == "run":
            if self.comm_id in BROWSER.pipes:
                BROWSER.request(self.comm_id, content.get("gen"))

    def on_msg(self, callback) -> None:
        """Nothing in the harness speaks back over the custom-message channel."""

    def on_close(self, callback) -> None:
        """Comms are never closed during a benchmark run."""

    def close(self, *args, **kwargs) -> None:
        """Comms are never closed during a benchmark run."""


class ElkNode:
    """Persistent ``node -e`` process running real elkjs on a file per request."""

    def __init__(self) -> None:
        candidates = [
            os.environ.get("IPYELK_BENCH_NODE"),
            str(ROOT / ".pixi" / "envs" / "dev" / "bin" / "node"),
            shutil.which("node"),
        ]
        node = next((c for c in candidates if c and Path(c).exists()), None)
        elkjs = os.environ.get("IPYELK_BENCH_ELKJS") or str(
            ROOT / "node_modules" / "elkjs" / "lib" / "elk.bundled.js"
        )
        if not node:
            raise SystemExit("no node found; set IPYELK_BENCH_NODE")
        if not Path(elkjs).exists():
            raise SystemExit(f"no elkjs at {elkjs}; set IPYELK_BENCH_ELKJS")
        self.proc = subprocess.Popen(
            [node, "-e", NODE_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "IPYELK_BENCH_ELKJS": elkjs},
        )
        self.tmp = Path(tempfile.mkdtemp(prefix="ipyelk-bench-"))
        self.last: dict = {}

    def layout(self, graph_json: str) -> str:
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        path = self.tmp / f"{uuid.uuid4().hex}.json"
        path.write_text(graph_json, encoding="utf-8")
        self.proc.stdin.write(f"{path}\n")
        self.proc.stdin.flush()
        self.last = json.loads(self.proc.stdout.readline())
        if not self.last.get("ok"):
            raise RuntimeError(f"elkjs failed: {self.last.get('error')}")
        out_path = path.with_suffix(".json.out.json")
        out = out_path.read_text(encoding="utf-8")
        path.unlink()
        out_path.unlink()
        return out

    def close(self) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.close()
        self.proc.wait(timeout=30)
        shutil.rmtree(self.tmp, ignore_errors=True)


ELK: ElkNode | None = None


def _timed(func, label: str):
    def wrapper(*args, **kwargs):
        with timed(label):
            return func(*args, **kwargs)

    return wrapper


def _timed_run(orig_run, label: str):
    async def run(self):
        with timed_pipe(label):
            return await orig_run(self)

    return run


def install_patches() -> None:
    """Instrument the widget/comm layer only -- ``src/`` is never edited."""
    import comm
    import ipywidgets.widgets.widget as widget_mod

    from ipyelk.pipes import ValidationPipe, VisibilityPipe, marks

    comm.create_comm = lambda *_args, **kwargs: RecordingComm(**kwargs)

    meta = marks.MarkElementWidget.value.metadata
    meta["to_json"] = _timed(meta["to_json"], "to_json (pydantic dump)")
    meta["from_json"] = _timed(meta["from_json"], "from_json (convert_elkjson rebuild)")
    marks.MarkElementWidget.persist = _timed(
        marks.MarkElementWidget.persist, "persist (index merge)"
    )
    widget_mod._remove_buffers = _timed(
        widget_mod._remove_buffers, "ipywidgets _remove_buffers"
    )
    label = "ipywidgets lock-compare json"
    widget_mod.jsondumps = _timed(widget_mod.jsondumps, label)
    widget_mod.jsonloads = _timed(widget_mod.jsonloads, label)
    ValidationPipe.run = _timed_run(ValidationPipe.run, "ValidationPipe.run")
    VisibilityPipe.run = _timed_run(VisibilityPipe.run, "VisibilityPipe.run")


def iter_unsized_labels(el: dict):
    """The labels js/measure_text.ts would measure (its ``get_labels``)."""
    for label in el.get("labels") or []:
        shape = (label.get("properties") or {}).get("shape") or {}
        if not shape.get("width") or not shape.get("height"):
            yield label
    for key in ("ports", "children", "edges", "labels"):
        for child in el.get(key) or []:
            yield from iter_unsized_labels(child)


def kernel_receive(
    outlet, raw: str, gen: int | None = None, persist: bool = True
) -> None:
    """The real browser -> kernel path, as ipywidgets runs it."""
    RECORDER.inbound[0] += 1
    RECORDER.inbound[1] += len(raw)
    with timed("json.loads (comm in)"):
        parsed = json.loads(raw)
    state = {"value": parsed}
    if gen is not None:
        state["gen"] = gen  # a kernel without the trait ignores the key
    with timed("Widget.set_state (inbound)"):
        outlet.set_state(state)
    if persist:
        outlet.persist()


class StubBrowser:
    """A frontend that answers ``run`` requests after ``delay`` seconds.

    Mirrors ``RunQueue`` in ``js/layout_widget_util.ts``: one layout in flight
    per pipe, a re-sent request for that generation is ignored, a newer one
    is queued and started once when the current layout resolves. A request
    without a generation (an older kernel) coalesces into one trailing run.
    """

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.pipes: dict[str, object] = {}  # comm_id -> ElkJS pipe
        self.in_flight: dict[str, int] = {}
        self.queued: dict[str, int] = {}
        self.tasks: set[asyncio.Task] = set()

    def request(self, comm_id: str, gen: int | None) -> None:
        gen = gen or 0
        current = self.in_flight.get(comm_id)
        if current is None:
            self._launch(comm_id, gen)
            return
        queued = self.queued.get(comm_id)
        # versioned: nothing older than the in-flight or queued generation;
        # unversioned: at most one trailing run
        duplicate = (gen <= max(current, queued or 0)) if gen else (queued is not None)
        if duplicate:
            CALLS["browser stub: duplicate run ignored"] += 1
        else:
            self.queued[comm_id] = gen

    def _launch(self, comm_id: str, gen: int) -> None:
        self.in_flight[comm_id] = gen
        task = asyncio.get_running_loop().create_task(self._serve(comm_id, gen))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _serve(self, comm_id: str, gen: int) -> None:
        assert ELK is not None
        pipe = self.pipes[comm_id]
        try:
            await asyncio.sleep(self.delay)
            CALLS["browser stub: layouts"] += 1
            try:
                with timed("elkjs roundtrip (subprocess)"):
                    raw = ELK.layout(json.dumps(RECORDER.value_of(pipe.inlet)))
            except RuntimeError as err:
                # js/layout_widget.ts reports a failed layout instead of leaving
                # the kernel to wait out its deadline
                error = {"action": "error", "error": str(err)}
                pipe._handle_browser_msg(pipe, error, None)
                return
            PROF["elkjs layout (in node)"] += ELK.last["ms_layout"] / 1000
            PROF["elkjs strip/apply properties"] += ELK.last["ms_other"] / 1000
            kernel_receive(pipe.outlet, raw, gen=gen or None, persist=False)
        finally:
            self.in_flight.pop(comm_id, None)
            queued = self.queued.pop(comm_id, None)
            if queued is not None:
                self._launch(comm_id, queued)

    async def idle(self) -> None:
        """Wait until every in-flight and queued layout has been answered."""
        while self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)


BROWSER: StubBrowser | None = None


async def stub_text_sizer_run(self) -> None:  # ruff: ignore[unused-async]
    """Stand-in for js/measure_text.ts ``measure()``: fixed width per char."""
    if self.outlet is None:
        return
    self.send({"action": "run"})
    with timed("browser stub: text sizer"):
        data = json.loads(json.dumps(RECORDER.value_of(self.inlet)))
        for label in iter_unsized_labels(data):
            label["width"] = CHAR_WIDTH * len(label.get("text", ""))
            label["height"] = LINE_HEIGHT
            CALLS["labels measured"] += 1
        # the browser stamps a fresh `out` so the value always differs
        data["out"] = CALLS["browser stub: text sizer"]
        raw = json.dumps(data)
    kernel_receive(self.outlet, raw)


async def stub_elkjs_run(self) -> None:  # ruff: ignore[unused-async]
    """Stand-in for js/layout_widget.ts ``layout()``: real elkjs in node."""
    if self.outlet is None:
        return
    assert ELK is not None
    self.send({"action": "run"})
    with timed("elkjs roundtrip (subprocess)"):
        raw = ELK.layout(json.dumps(RECORDER.value_of(self.inlet)))
    PROF["elkjs layout (in node)"] += ELK.last["ms_layout"] / 1000
    PROF["elkjs strip/apply properties"] += ELK.last["ms_other"] / 1000
    CALLS["browser stub: layouts"] += 1
    kernel_receive(self.outlet, raw)


async def measure(diagram) -> dict:
    """One refresh, fully awaited, with the timers and comm log reset first."""
    start, inbound = len(RECORDER.log), tuple(RECORDER.inbound)
    PROF.clear()
    CALLS.clear()
    t0 = time.perf_counter()
    task = diagram.refresh()
    assert task is not None, "no running event loop"
    await task
    await asyncio.sleep(0)  # let Diagram.refresh's done-callback run
    if BROWSER is not None:
        await BROWSER.idle()  # a queued duplicate layout lands in this phase
    comm = RECORDER.summarize(start, inbound)

    return {
        "wall_s": time.perf_counter() - t0,
        "validation_s": PROF["ValidationPipe.run (excl sync)"],
        "visibility_s": PROF["VisibilityPipe.run (excl sync)"],
        "elkjs_s": PROF["elkjs layout (in node)"],
        "elkjs_roundtrip_s": PROF["elkjs roundtrip (subprocess)"],
        "text_sizer_stub_s": PROF["browser stub: text sizer"],
        "kernel_sync_s": sync_total(),
        "kernel_receive_s": PROF["Widget.set_state (inbound)"],
        "kernel_sync_breakdown": {label: PROF[label] for label in SYNC_LABELS},
        "labels_measured": CALLS["labels measured"],
        "layouts": CALLS["browser stub: layouts"],
        "layout_runs": comm["runs"].get("elk", 0),
        "sizer_runs": comm["runs"].get("sizer", 0),
        "comm": comm,
    }


def hide_nodes(pipe, fraction: float) -> list:
    """Hide a deterministic ~``fraction`` of the leaf nodes."""
    from ipyelk.elements import Node

    leaves = sorted(
        (
            el
            for el in pipe.inlet.index.elements.elements.values()
            if isinstance(el, Node) and el.get_parent() is not None and not el.children
        ),
        key=lambda el: str(el.get_id()),
    )
    chosen = leaves[:: max(1, round(1 / fraction))]
    for el in chosen:
        el.properties.hidden = True
    return chosen


def hide_incident_edges(pipe, hidden: list) -> int:
    """Work around the root-slack-port elkjs crash (#161 defect 10)."""
    from ipyelk.elements import Edge

    gone = set(hidden)
    count = 0
    for el in pipe.inlet.index.elements.elements.values():
        if isinstance(el, Edge) and set(el.points()) & gone:
            el.properties.hidden = True
            count += 1
    return count


async def run_case(shape: str, n: int) -> dict:
    """Build one graph, refresh it, collapse it, then burst it."""
    import bench_graphs

    from ipyelk.diagram import Diagram
    from ipyelk.loaders import ElementLoader
    from ipyelk.pipes import flows as F

    root = bench_graphs.GENERATORS[shape](n, seed=SEED)
    case: dict = {"shape": shape, "n": n, "elements": bench_graphs.count_elements(root)}
    RECORDER.enabled = False  # widget construction traffic is not refresh traffic
    source = ElementLoader().load(root=root)
    diagram = Diagram(source=source)
    pipe = diagram.pipe
    valid, sizer, vis, elk = pipe.pipes
    RECORDER.roles.update({
        source.comm.comm_id: "source",
        valid.outlet.comm.comm_id: "valid.out/sizer.in",
        sizer.outlet.comm.comm_id: "sizer.out",
        vis.outlet.comm.comm_id: "vis.out/elk.in",
        elk.outlet.comm.comm_id: "elk.out/view.source",
        sizer.comm.comm_id: "sizer",
        elk.comm.comm_id: "elk",
    })
    if BROWSER is not None:
        BROWSER.pipes[elk.comm.comm_id] = elk
    RECORDER.enabled = True

    case["first"] = await measure(diagram)
    case["laid_out_bytes"] = len(
        json.dumps(elk.outlet.value.model_dump(mode="json", exclude_none=True))
    )

    hidden = hide_nodes(pipe, HIDDEN_FRACTION)
    case["hidden_nodes"] = len(hidden)
    pipe.inlet.flow = (F.Node.hidden,)
    try:
        case["collapse"] = await measure(diagram)
    except Exception as err:
        case["collapse"] = None
        case["collapse_error"] = f"{type(err).__name__}: {err}"[:300]
        case["hidden_edges"] = hide_incident_edges(pipe, hidden)
        pipe.inlet.flow = (F.Node.hidden,)
        case["collapse_workaround"] = await measure(diagram)

    # burst: ten refresh() calls in one tick after one flow change
    start, inbound = len(RECORDER.log), tuple(RECORDER.inbound)
    CALLS["browser stub: layouts"] = 0
    pipe.inlet.flow = (F.Node.hidden,)
    tasks = [t for t in (diagram.refresh() for _ in range(BURST)) if t is not None]
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0)
    if BROWSER is not None:
        await BROWSER.idle()
    burst = RECORDER.summarize(start, inbound)
    case["burst"] = {
        "refresh_calls": BURST,
        "layouts": CALLS["browser stub: layouts"],
        "layout_runs": burst["runs"].get("elk", 0),
        "sizer_runs": burst["runs"].get("sizer", 0),
        "messages": burst["messages"]["total"],
        "bytes": burst["bytes"]["total"],
        "browser_to_kernel": burst["browser_to_kernel"],
    }
    return case


def fmt_s(value: float) -> str:
    return f"{value * 1000:.0f} ms" if value < 1 else f"{value:.2f} s"


def fmt_b(value: float) -> str:
    if value < 1024 * 1024:
        return f"{value / 1024:.0f} KB"
    return f"{value / 1024 / 1024:.2f} MB"


def table(header: list[str], rows: list[list[str]]) -> str:
    align = ["---", *["---:"] * (len(header) - 1)]
    return "\n".join(f"| {' | '.join(row)} |" for row in (header, align, *rows) if row)


BURST_KEYS = ("refresh_calls", "layout_runs", "layouts", "sizer_runs", "messages")
REFRESH_HEADER = [
    "Graph", "Elements", "Wall", "Validation", "Visibility", "elkjs",
    "Kernel sync", "Msgs", "update", "echo", "custom", "Bytes", "Runs", "Layouts",
]  # fmt: skip


def name(case: dict) -> str:
    return f"{case['shape']} {case['n']}"


def refresh_row(case: dict, key: str) -> list[str] | None:
    data = case.get(key)
    if not data:
        return None
    msgs = data["comm"]["messages"]
    return [
        name(case) + (" (edges hidden too)" if key == "collapse_workaround" else ""),
        str(case["elements"]["total"]),
        *(
            fmt_s(data[k])
            for k in ("wall_s", "validation_s", "visibility_s", "elkjs_s")
        ),
        fmt_s(data["kernel_sync_s"]),
        *(str(msgs.get(k, 0)) for k in ("total", "update", "echo_update", "custom")),
        fmt_b(data["comm"]["bytes"]["total"]),
        str(data["layout_runs"]),
        str(data.get("layouts", data["layout_runs"])),
    ]


def render(results: dict) -> str:
    cases = results["cases"]
    out = [f"## ipyelk pipeline benchmark: `{results['label']}`"]
    if results.get("slow_browser"):
        out[0] += f" (browser answers after {results['slow_browser']} s)"

    sections = [
        (
            "Graphs",
            ["Graph", "Breakdown", "Elements", "Depth", "Laid-out JSON"],
            [
                [
                    name(c),
                    ", ".join(
                        f"{k}={v}"
                        for k, v in c["elements"].items()
                        if k not in ("total", "depth")
                    ),
                    str(c["elements"]["total"]),
                    str(c["elements"]["depth"]),
                    fmt_b(c["laid_out_bytes"]),
                ]
                for c in cases
            ],
        ),
        (
            "First refresh",
            REFRESH_HEADER,
            [refresh_row(c, "first") for c in cases],
        ),
        (
            f"Second refresh, ~{HIDDEN_FRACTION:.0%} of nodes hidden",
            REFRESH_HEADER,
            [
                row
                for c in cases
                for key in ("collapse", "collapse_workaround")
                if (row := refresh_row(c, key))
            ],
        ),
        (
            f"Burst: {BURST} `refresh()` calls in one tick",
            [
                "Graph",
                "refresh()",
                "Layout runs",
                "Layouts",
                "Sizer runs",
                "Msgs",
                "Bytes",
            ],
            [
                [
                    name(c),
                    *(str(c["burst"][k]) for k in BURST_KEYS),
                    fmt_b(c["burst"]["bytes"]),
                ]
                for c in cases
            ],
        ),
    ]
    for title, header, rows in sections:
        out += ["", f"### {title}", "", table(header, rows)]
    errors = [
        f"- `{name(c)}`: {c['collapse_error']}"
        for c in cases
        if c.get("collapse_error")
    ]
    if errors:
        out += ["", "Collapse failed (hidden node with visible edges):", "", *errors]
    return "\n".join(out)


async def main_async(args) -> dict:
    global BROWSER, ELK  # ruff: ignore[global-statement]
    install_patches()

    import ipyelk.pipes.elkjs as elkjs_mod
    import ipyelk.pipes.text_sizer as text_sizer_mod

    text_sizer_mod.BrowserTextSizer.run = stub_text_sizer_run
    if args.slow_browser:
        # keep the real ElkJS.run (browser_roundtrip + persist); the stub
        # browser answers the comm messages it sends
        BROWSER = StubBrowser(args.slow_browser)
    else:
        elkjs_mod.ElkJS.run = stub_elkjs_run

    ELK = ElkNode()
    results: dict = {
        "label": args.label,
        "seed": SEED,
        "hidden_fraction": HIDDEN_FRACTION,
        "burst": BURST,
        "slow_browser": args.slow_browser,
        "cases": [],
    }

    try:
        for shape in args.shapes:
            for n in args.sizes:
                print(f"[bench] {shape} {n} ...", file=sys.stderr, flush=True)
                results["cases"].append(await run_case(shape, n))
    finally:
        ELK.close()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True, help="name of this run")
    parser.add_argument("--sizes", type=int, nargs="+", default=list(SIZES))
    parser.add_argument("--shapes", nargs="+", default=list(SHAPES), choices=SHAPES)
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "bench")
    parser.add_argument(
        "--slow-browser",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="answer each layout request after this delay through the real "
        "ElkJS.run (0: stub answers the first request immediately)",
    )

    args = parser.parse_args(argv)
    if args.slow_browser:
        # the stub browser answers the real roundtrip; headless mode would
        # short-circuit it with an immediate TimeoutError
        os.environ.pop("IPYELK_NO_BROWSER", None)

    results = asyncio.run(main_async(args))

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{args.label}.json"
    path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    print(render(results))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
