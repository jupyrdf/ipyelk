# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "check_todos.py"
spec = importlib.util.spec_from_file_location("check_todos", SCRIPT)
assert spec
assert spec.loader
check_todos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_todos)

# built from parts, so that this file passes the check it tests
WORDS = ["TO" + "DO", "FIX" + "ME", "X" + "XX", "HA" + "CK"]


@pytest.mark.parametrize("word", WORDS)
def test_a_marker_with_an_issue_passes(word):
    assert not list(check_todos.untracked(f"# {word}(#123): fix the thing"))
    assert not list(check_todos.untracked(f"// {word}(#7): and in TypeScript"))


@pytest.mark.parametrize("word", WORDS)
@pytest.mark.parametrize(
    "line",
    [
        "# {word} fix the thing",
        "# {word}: fix the thing",
        "# {word}: #123 an issue that is not in the marker",
        "# {word}(#): no number",
        "# {word}(123): no hash",
    ],
)
def test_a_marker_without_an_issue_is_reported(word, line):
    text = "x = 1\n" + line.format(word=word) + "\n"
    assert [number for number, _ in check_todos.untracked(text)] == [2]


def test_words_that_only_contain_a_marker_pass():
    assert not list(check_todos.untracked("todo_list = mastodon = 'HACKATHON'"))
