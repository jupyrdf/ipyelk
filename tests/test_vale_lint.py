# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "vale_lint.py"
spec = importlib.util.spec_from_file_location("vale_lint", SCRIPT)
assert spec
assert spec.loader
vale_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vale_lint)

ALERT = {
    "Check": "IPyElk.Spelling",
    "Line": 3,
    "Message": "Did you really mean 'recieve'?",
    "Severity": "error",
    "Span": [5, 11],
}

FAKE_VALE = """
import json, os, sys
mode = os.environ["FAKE_VALE"]
ext = next((a[6:] for a in sys.argv if a.startswith("--ext=")), None)
if ext:
    canary = {} if mode == "blind" else {"stdin" + ext: [ALERT]}
    print(json.dumps(canary))
elif mode == "crash":
    print("panic: runtime error", file=sys.stderr)
    sys.exit(2)
else:
    print({
        "clean": "{}",
        "findings": json.dumps({"README.md": [ALERT]}),
        "empty": "",
        "partial": '{"src/x.py": [',
        "shape": json.dumps({"README.md": {"Line": 1}}),
    }[mode])
"""


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    fake = tmp_path / "fake_vale.py"
    fake.write_text(f"ALERT = {ALERT!r}\n{FAKE_VALE}", encoding="utf-8")
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    monkeypatch.setattr(vale_lint, "ROOT", tmp_path)
    monkeypatch.setattr(vale_lint, "VALE", [sys.executable, str(fake)])
    monkeypatch.setattr(vale_lint, "PATHS", ["README.md"])

    def run(mode, paths=None):
        monkeypatch.setenv("FAKE_VALE", mode)
        if paths is not None:
            monkeypatch.setattr(vale_lint, "PATHS", paths)
        code = vale_lint.main()
        return code, capsys.readouterr()

    return run


def test_clean_passes(run):
    code, out = run("clean")
    assert code == 0, out
    assert "vale: 0 warning(s) or error(s)" in out.out


def test_findings_fail_with_path_and_line(run):
    code, out = run("findings")
    assert code == 1, out
    assert "README.md:3:5: error [IPyElk.Spelling]" in out.out


@pytest.mark.parametrize("mode", ["crash", "empty", "partial", "shape", "blind"])
def test_broken_vale_fails(run, mode):
    code, out = run(mode)
    assert code == 2, out
    assert "!!!" in out.err


def test_crash_shows_stderr(run):
    _, out = run("crash")
    assert "panic: runtime error" in out.err


@pytest.mark.parametrize("paths", [["nope"], ["empty_dir"]])
def test_missing_or_empty_path_fails(run, tmp_path, paths):
    (tmp_path / "empty_dir").mkdir()
    code, out = run("clean", paths)
    assert code == 2, out
    assert paths[0] in out.err


def test_parse_accepts_real_shape():
    assert vale_lint.parse(json.dumps({"a.md": [ALERT]})) == {"a.md": [ALERT]}
