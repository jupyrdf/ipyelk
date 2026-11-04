# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Browser benchmark of sprotty rendering with viewport culling off and on.

    pixi run bench-render

The measurement behind jupyrdf/ipyelk#170. It renders laid-out graphs (from
``bench_render_fixtures.py``; built on demand) in a real, headless browser --
by default the Firefox the acceptance tests use -- through the extension's own
sprotty container (``scripts/bench_render/entry.ts``, bundled with ``vite``), and
times each kind of update a view performs:

``first``
    the first render of the model into an empty DOM (once per case);
``render``
    one forced ``ModelViewer.update`` of the current model: every view function
    runs (culling included) and ``snabbdom`` diffs a DOM that does not change;
``select`` / ``hover``
    a ``SelectAction`` / ``HoverFeedbackAction`` on one node -- what a click or
    a mouse move costs, and what ``diagramUpdated`` fires on;
``pan``
    a non-animated ``SetViewportAction`` a tenth of a canvas sideways;
``relayout``
    ``JLModelSource.updateLayout`` with the same layout: what a kernel refresh
    costs, including sprotty's update animation (many renders).

Every op is measured at ``fit`` (the whole diagram on screen, the normal path;
sprotty's zoom floor of 0.01 keeps a huge diagram partly off screen even then)
and at each ``--zooms`` level centered on the content (so most of the
graph is off screen), with culling off and on. The combinations are
interleaved round by round (``--rounds``) so JIT warm-up and garbage collection
drift hit each of them alike; one extra first round warms up and is dropped.

Per sample, ``render`` is the time inside ``ModelViewer.update`` (view
functions, the culling walk, the ``snabbdom`` patch); ``dispatch`` is the whole
action; ``layout`` is a forced ``getBBox()`` on the diagram group afterwards
(the style and SVG geometry work the DOM change left pending); ``frame`` is
the time to the second animation frame after the dispatch, which a headless
browser rounds up to its refresh interval, so it only resolves differences of
a frame or more. Paint itself cannot be timed from a page. The report gives
medians with the 10th and 90th percentiles over all kept samples, and the DOM
element counts at each viewport, which is what the exporter and the robot
suites would see.

Where neither Firefox nor Chrome will launch under WebDriver (macOS sandboxes
the pixi Firefox), ``scripts/bench_render/playwright.mjs`` drives the same page
with Playwright and writes the raw result, which ``--results FILE`` turns into
the same report.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = ROOT / "build" / "bench-render"
SITE = BUILD / "site"
FIXTURES = BUILD / "fixtures"
sys.path.insert(0, str(HERE))

OPS = ("render", "select", "hover", "pan", "relayout")
DEFAULT_CASES = ("flat:1000", "nested:1000")
METRICS = ("render", "dispatch", "layout", "frame")
#: `statistics.quantiles` needs at least this many values
MIN_QUANTILE_SAMPLES = 2


def build_site(skip: bool) -> None:
    if skip and (SITE / "index.html").exists():
        return
    vite = ROOT / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if not vite.exists():
        raise SystemExit(f"no vite at {vite}: run `pixi run setup-js` first")
    config = HERE / "bench_render" / "vite.config.mts"
    print(f"[bench] building {SITE} ...", file=sys.stderr, flush=True)
    subprocess.check_call([str(vite), "build", "--config", str(config)], cwd=ROOT)


def parse_case(case: str) -> tuple[str, int]:
    shape, _, n = case.partition(":")
    if not n.isdigit():
        raise SystemExit(f"bad case {case!r}: expected SHAPE:N")
    return shape, int(n)


def ensure_fixtures(cases: list[str]) -> None:
    import bench_render_fixtures

    missing = [
        case
        for case in cases
        if not bench_render_fixtures.fixture_path(FIXTURES, *parse_case(case)).exists()
    ]
    if missing:
        print(f"[bench] building fixtures {missing} ...", file=sys.stderr, flush=True)
        bench_render_fixtures.main(["--cases", *missing, "--out", str(FIXTURES)])


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        pass


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def firefox(headless: bool):
    from selenium import webdriver
    from selenium.webdriver.firefox.service import Service

    binary = os.environ.get("FIREFOX") or shutil.which("firefox")
    driver_path = os.environ.get("GECKODRIVER") or shutil.which("geckodriver")
    if not binary or not driver_path:
        raise SystemExit(
            "no firefox/geckodriver on PATH: run under `pixi run -e atest`, or set "
            "FIREFOX and GECKODRIVER"
        )
    options = webdriver.FirefoxOptions()
    options.binary_location = binary
    if headless:
        options.add_argument("-headless")
    log = BUILD / "geckodriver.log"
    BUILD.mkdir(parents=True, exist_ok=True)
    return webdriver.Firefox(
        options=options, service=Service(driver_path, log_output=str(log))
    )


def chrome(headless: bool):
    from selenium import webdriver

    options = webdriver.ChromeOptions()
    binary = os.environ.get("CHROME")
    if binary:
        options.binary_location = binary
    if headless:
        options.add_argument("--headless=new")
    # selenium manager finds or fetches a matching ``chromedriver``
    return webdriver.Chrome(options=options)


BROWSERS = {"firefox": firefox, "chrome": chrome}

RUN_ALL = """
const [config] = arguments;
const done = arguments[arguments.length - 1];
window.elkBench.runAll(config).then(
  (result) => done({ ok: true, result }),
  (err) => done({ ok: false, error: String((err && err.stack) || err) }),
);
"""


def run_in_browser(args, config: dict) -> dict:
    server, base = serve(BUILD)
    driver = BROWSERS[args.browser](headless=not args.no_headless)
    try:
        driver.set_window_size(1400, 1000)
        driver.set_script_timeout(args.timeout)
        driver.get(f"{base}/site/index.html")
        print(f"[bench] running {config} ...", file=sys.stderr, flush=True)
        reply = driver.execute_async_script(RUN_ALL, config)
        if not reply.get("ok"):
            raise RuntimeError(f"the benchmark page failed: {reply.get('error')}")
        result = reply["result"]
        caps = driver.capabilities
        result["browser"] = (
            f"{caps.get('browserName')} {caps.get('browserVersion')}"
            f" ({'headed' if args.no_headless else 'headless'})"
        )
        return result
    finally:
        driver.quit()
        server.shutdown()


def quantiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    values = sorted(values)
    q = (
        statistics.quantiles(values, n=10)
        if len(values) >= MIN_QUANTILE_SAMPLES
        else [values[0]] * 9
    )
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p10": q[0],
        "p90": q[-1],
        "min": values[0],
        "max": values[-1],
    }


def summarize(case: dict) -> dict:
    summary = {}
    for key, run in case["runs"].items():
        by_op: dict[str, dict] = {}
        for op in OPS:
            samples = [s for s in run["samples"] if s["op"] == op]
            if not samples:
                continue
            by_op[op] = {
                metric: quantiles([s[metric] for s in samples]) for metric in METRICS
            }
            by_op[op]["updates"] = quantiles([s["updates"] for s in samples])
        summary[key] = {
            "culling": run["culling"],
            "viewport": run["viewport"],
            "camera": run["camera"],
            "dom": run["dom"],
            "ops": by_op,
        }
    return summary


def fmt(q: dict, digits: int = 1) -> str:
    if not q.get("n"):
        return "-"
    return f"{q['median']:.{digits}f} [{q['p10']:.{digits}f}-{q['p90']:.{digits}f}]"


def render_markdown(results: dict) -> str:
    config = results["config"]
    canvas = results["canvas"]
    setup = (
        f"{results['browser']} on {results['platform']}; canvas "
        f"{canvas['width']}x{canvas['height']}; zoom {', '.join(f'{z:g}' for z in config['zooms'])}"
        f" centered on the content; {config['rounds']} rounds x {config['repeat']} repeats per op after "
        "one dropped warm-up round; ms as median [p10-p90]"
    )
    out = [f"# render benchmark: {results['label']}", "", setup, ""]
    for case in results["cases"]:
        el = case["elements"]
        first = case["first"]
        heading = (
            f"## {case['case']}: {el.get('Node', 0)} nodes, {el.get('Edge', 0)} edges, "
            f"{el.get('Label', 0)} labels, {el.get('Port', 0)} ports, depth {el['depth']}"
        )
        first_line = (
            f"first render (culling off, 1:1 at the origin): render {first['render']:.0f}"
            f" ms, dispatch {first['dispatch']:.0f} ms, layout {first['layout']:.0f} ms,"
            f" frame {first['frame']:.0f} ms"
        )
        out.extend([
            heading,
            "",
            first_line,
            "",
            "| culling | viewport | DOM nodes / edges / labels | svg chars |",
            "|---|---|---:|---:|",
        ])
        for run in case["summary"].values():
            dom = run["dom"]
            out.append(
                f"| {'on' if run['culling'] else 'off'} | {run['viewport']} | "
                f"{dom['nodes']} / {dom['edges']} / {dom['labels']} | {dom['svgChars']:,} |"
            )
        columns = (
            "| op | culling | viewport | n | render ms | dispatch ms | layout ms | "
            "frame ms | updates |"
        )
        out.extend(["", columns, "|---|---|---|---:|---:|---:|---:|---:|---:|"])
        for op in OPS:
            for run in case["summary"].values():
                q = run["ops"].get(op)
                if not q:
                    continue
                out.append(
                    f"| {op} | {'on' if run['culling'] else 'off'} | {run['viewport']} | "
                    f"{q['render']['n']} | {fmt(q['render'])} | {fmt(q['dispatch'])} | "
                    f"{fmt(q['layout'])} | {fmt(q['frame'])} | "
                    f"{q['updates']['median']:g} |"
                )
        out.append("")
    return "\n".join(out)


def report(results: dict, label: str, out: Path) -> str:
    results["label"] = label
    results.setdefault("platform", f"{platform.system()} {platform.machine()}")
    results.setdefault("browser", results.get("userAgent", "?"))
    for case in results["cases"]:
        case["summary"] = summarize(case)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{label}.json").write_text(json.dumps(results, indent=1))
    markdown = render_markdown(results)
    (out / f"{label}.md").write_text(markdown)
    return markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True, help="name of this run")
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument("--ops", nargs="+", default=list(OPS), choices=OPS)
    parser.add_argument("--rounds", type=int, default=5, help="kept rounds")
    parser.add_argument("--repeat", type=int, default=5, help="ops per round")
    parser.add_argument(
        "--zooms",
        type=float,
        nargs="+",
        default=[1.0],
        help="the zoomed viewports, each centered on the content",
    )
    parser.add_argument("--browser", choices=sorted(BROWSERS), default="firefox")
    parser.add_argument("--timeout", type=int, default=3600, help="seconds, in-page")
    parser.add_argument("--out", type=Path, default=BUILD)
    parser.add_argument("--skip-build", action="store_true", help="reuse the site")
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument(
        "--results",
        type=Path,
        help="report a raw result another driver wrote instead of running a browser",
    )
    args = parser.parse_args(argv)

    if args.results:
        results = json.loads(args.results.read_text())
    else:
        ensure_fixtures(args.cases)
        build_site(args.skip_build)
        config = {
            "fixtures": [
                f"../fixtures/{shape}-{n}.json"
                for shape, n in map(parse_case, args.cases)
            ],
            "ops": list(args.ops),
            "rounds": args.rounds,
            "repeat": args.repeat,
            "zooms": args.zooms,
        }
        results = run_in_browser(args, config)
    print(report(results, args.label, args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
