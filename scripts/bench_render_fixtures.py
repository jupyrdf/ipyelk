# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Laid-out graphs for ``bench_render.py``: what a browser view receives.

    pixi run -e utest python scripts/bench_render_fixtures.py --cases flat:1000

Runs ``bench_pipeline.py``'s harness -- the kernel-side pipeline with the text
sizer stubbed (fixed width per character) and real elkjs in node -- on the
``bench_graphs.py`` shapes, and writes one JSON file per case to
``build/bench-render/fixtures/<shape>-<n>.json`` holding the pipe outlet's
``value`` (the ``ELKViewerModel.source`` value the browser renders) and the
diagram's ``symbols``, exactly as ``elements.serialization.to_json`` puts them
on the wire. A file that already exists is kept unless ``--force``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

os.environ.setdefault("IPYELK_NO_BROWSER", "1")
os.environ.setdefault("IPYELK_TESTING", "1")

import bench_graphs  # ruff: ignore[module-import-not-at-top-of-file]
import bench_pipeline as bp  # ruff: ignore[module-import-not-at-top-of-file]

DEFAULT_CASES = ("flat:1000", "nested:1000")


async def dump_case(shape: str, n: int, path: Path) -> None:
    from ipyelk.diagram import Diagram
    from ipyelk.elements.serialization import to_json
    from ipyelk.loaders import ElementLoader

    t0 = time.perf_counter()
    root = bench_graphs.GENERATORS[shape](n, seed=bp.SEED)
    source = ElementLoader().load(root=root)
    diagram = Diagram(source=source)
    task = diagram.refresh()
    assert task is not None, "no running event loop"
    await task
    await asyncio.sleep(0)
    layout = to_json(diagram.pipe.outlet.value, None)
    assert layout is not None, "the pipeline produced no layout"
    fixture = {
        "shape": shape,
        "n": n,
        "seed": bp.SEED,
        "elements": bench_graphs.count_elements(root),
        "layout": layout,
        "symbols": to_json(diagram.symbols, None),
    }
    size = write_fixture(path, fixture)
    print(
        f"[fixtures] {shape} {n}: {size / 1e6:.2f} MB"
        f" in {time.perf_counter() - t0:.1f} s -> {path}",
        file=sys.stderr,
        flush=True,
    )
    diagram.close()
    bp.reset_case()


def write_fixture(path: Path, fixture: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path.stat().st_size


def fixture_path(out: Path, shape: str, n: int) -> Path:
    return out / f"{shape}-{n}.json"


async def main_async(cases: list[tuple[str, int]], out: Path, force: bool) -> int:
    pending = [
        (s, n) for s, n in cases if force or not fixture_path(out, s, n).exists()
    ]
    for shape, n in cases:
        if (shape, n) not in pending:
            print(f"[fixtures] {shape} {n}: kept {fixture_path(out, shape, n)}")
    if not pending:
        return 0

    bp.install_patches()

    import ipyelk.pipes.elkjs as elkjs_mod
    import ipyelk.pipes.text_sizer as text_sizer_mod

    text_sizer_mod.BrowserTextSizer.run = bp.stub_text_sizer_run
    elkjs_mod.ElkJS.run = bp.stub_elkjs_run
    bp.ELK = bp.ElkNode()
    try:
        for shape, n in pending:
            await dump_case(shape, n, fixture_path(out, shape, n))
    finally:
        bp.ELK.close()
    return 0


def parse_cases(cases: list[str]) -> list[tuple[str, int]]:
    parsed = []
    for case in cases:
        shape, _, n = case.partition(":")
        if shape not in bench_graphs.GENERATORS or not n.isdigit():
            raise SystemExit(f"bad case {case!r}: expected SHAPE:N")
        parsed.append((shape, int(n)))
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument(
        "--out", type=Path, default=ROOT / "build" / "bench-render" / "fixtures"
    )
    parser.add_argument("--force", action="store_true", help="rebuild existing files")
    args = parser.parse_args(argv)
    return asyncio.run(main_async(parse_cases(args.cases), args.out, args.force))


if __name__ == "__main__":
    sys.exit(main())
