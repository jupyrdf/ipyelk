# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "bench_check.py"
spec = importlib.util.spec_from_file_location("bench_check", SCRIPT)
assert spec
assert spec.loader
bench_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench_check)


def phase(name, **counts):
    """One phase as ``bench_pipeline.py`` writes it: only ``burst`` has ``errors``."""
    base = dict.fromkeys(set(bench_check.COUNTS) - {"errors"}, 1)
    base["wall_s"] = 0.5
    if name == "burst":
        base["errors"] = []
    base.update(counts)
    return base


def results(label="fast", slow=0.0, collapse_failed=False, **counts):
    case = {"shape": "flat", "n": 10}
    case.update({name: phase(name, **counts) for name in bench_check.PHASES})
    if collapse_failed:
        case["collapse"] = None
    return {"label": label, "slow_browser": slow, "cases": [case]}


@pytest.fixture
def run(tmp_path):
    def run(baseline_results, actual_results, *extra):
        baseline = tmp_path / "baseline.json"
        for name, data in (("old", baseline_results), ("new", actual_results)):
            (tmp_path / name).mkdir(exist_ok=True)
            (tmp_path / name / f"{data['label']}.json").write_text(json.dumps(data))
        old = tmp_path / "old" / f"{baseline_results['label']}.json"
        new = tmp_path / "new" / f"{actual_results['label']}.json"
        bench_check.main(["--update", "--baseline", str(baseline), str(old)])
        return bench_check.main(["--baseline", str(baseline), str(new), *extra])

    return run


def test_matching_counts_pass(run):
    assert run(results(), results()) == 0


def test_timings_are_not_gated(run):
    slower = results()
    for name in bench_check.PHASES:
        slower["cases"][0][name]["wall_s"] = 50.0
    assert run(results(), slower) == 0


@pytest.mark.parametrize("value", [0, 2])
def test_any_count_change_fails(run, value):
    assert run(results(), results(comm_opens=value)) == 1


def test_errors_fail(run):
    assert run(results(), results(errors=["boom"])) == 1


def test_failed_phase_fails_without_a_traceback(run):
    assert run(results(), results(collapse_failed=True)) == 1


def test_only_recorded_errors_are_gated():
    flat = bench_check.gated("fast", results())
    assert [key for key in flat if key.endswith(" errors")] == [
        "fast flat:10 burst errors"
    ]


def test_missing_case_fails(run):
    assert run(results(), results(label="other")) == 1


def test_slow_browser_gates_only_timing_independent_counts():
    flat = bench_check.gated("slow", results(slow=0.75, layout_runs=7))
    assert {key.rsplit(" ", 1)[1] for key in flat} == {
        "layouts",
        "errors",
        "failed",
        "live_widgets_added",
    }


def test_compare_labels_direction():
    problems = bench_check.compare({"a": 1, "b": 1, "c": 1}, {"a": 2, "b": 0, "d": 1})
    assert [problem.split()[0] for problem in problems] == [
        "REGRESSION",
        "IMPROVED",
        "MISSING",
        "NEW",
    ]
