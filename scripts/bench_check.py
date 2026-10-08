# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Gate ``bench_pipeline.py`` results against a committed baseline.

Only deterministic counts are gated (messages, bytes, comm opens, layouts,
live widgets left by replacing a pipe or closing a diagram); they must equal the
baseline exactly.
A count that rises is a regression; a count that falls is an improvement that
must be locked in with ``--update``, so every change to the pipeline's cost
shows up as a reviewed baseline diff.
Timings vary between machines and are reported, never gated.

    python scripts/bench_check.py build/reports/bench/*.json
    python scripts/bench_check.py --update build/reports/bench/*.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
BASELINE = HERE / "bench_baseline.json"
PHASES = ("first", "collapse", "burst", "replace", "close")
COUNTS = (
    "comm_opens",
    "messages_k2b",
    "messages_b2k",
    "bytes_k2b",
    "bytes_b2k",
    "layout_runs",
    "layouts",
    "sizer_runs",
    "errors",
    "live_widgets_added",
)
#: a ``--slow-browser`` run's resend counts depend on timing: gate only these
SLOW_COUNTS = ("layouts", "errors", "live_widgets_added")


def gated(label: str, results: dict) -> dict[str, int]:
    """Flatten one results file to ``{"<label> <shape>:<n> <phase> <count>": value}``.

    A phase the benchmark could not complete (``None``) counts as ``failed: 1``.
    """
    names = SLOW_COUNTS if results.get("slow_browser") else COUNTS
    flat = {}
    for case in results["cases"]:
        for phase in PHASES:
            prefix = f"{label} {case['shape']}:{case['n']} {phase}"
            metrics = case.get(phase)
            flat[f"{prefix} failed"] = int(metrics is None)
            for name in names if metrics else ():
                value = metrics.get(name)
                if name == "errors" and value is not None:
                    value = len(value)
                if value is not None:
                    flat[f"{prefix} {name}"] = value
    return flat


def timings(label: str, results: dict) -> list[str]:
    return [
        f"| {label} | {case['shape']}:{case['n']} | {phase} "
        f"| {case[phase]['wall_s'] * 1000:.0f} ms |"
        for case in results["cases"]
        for phase in PHASES
        if case.get(phase)
    ]


def compare(baseline: dict[str, int], actual: dict[str, int]) -> list[str]:
    problems = []
    for key in sorted(baseline.keys() | actual.keys()):
        want, got = baseline.get(key), actual.get(key)
        if want is None:
            problems.append(f"NEW        {key} = {got} (not in the baseline)")
        elif got is None:
            problems.append(f"MISSING    {key} (baseline {want})")
        elif got > want:
            problems.append(f"REGRESSION {key}: {want} -> {got}")
        elif got < want:
            problems.append(f"IMPROVED   {key}: {want} -> {got}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument(
        "--update", action="store_true", help="rewrite the baseline from results"
    )
    args = parser.parse_args(argv)

    actual: dict[str, int] = {}
    rows: list[str] = []
    for path in args.results:
        results = json.loads(path.read_text(encoding="utf-8"))
        label = results.get("label") or path.stem
        actual.update(gated(label, results))
        rows += timings(label, results)

    summary = "\n".join([
        "### Pipeline benchmark wall time (not gated)",
        "",
        "| run | case | phase | wall |",
        "| --- | --- | --- | ---: |",
        *rows,
    ])
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as fh:
            fh.write(summary + "\n")

    if args.update:
        text = json.dumps(actual, indent=2, sort_keys=True) + "\n"
        args.baseline.write_text(text, encoding="utf-8")
        print(f"\nwrote {len(actual)} counts to {args.baseline}")
        return 0

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    problems = compare(baseline, actual)
    if not problems:
        print(f"\n{len(actual)} counts match {args.baseline.name}")
        return 0
    print(f"\n{len(problems)} count(s) differ from {args.baseline.name}:")
    print("\n".join(f"  {problem}" for problem in problems))
    print(
        "\nIf the change is intended, run `pixi run bench-update` and commit "
        f"{args.baseline.name} so the new counts are reviewed."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
