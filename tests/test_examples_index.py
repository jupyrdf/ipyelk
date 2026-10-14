# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Every example notebook is linked from ``examples/_index.ipynb``."""

import json
import re
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parents[1] / "examples"
INDEX = EXAMPLES / "_index.ipynb"

pytestmark = pytest.mark.skipif(
    not INDEX.exists(), reason="the source distribution has no examples"
)


def test_the_index_links_every_example():
    cells = json.loads(INDEX.read_text(encoding="utf-8"))["cells"]
    text = "".join("".join(c["source"]) for c in cells if c["cell_type"] == "markdown")
    linked = set(re.findall(r"\]\(\./([^)]+\.ipynb)\)", text))
    examples = {path.name for path in EXAMPLES.glob("[0-9]*.ipynb")}
    assert sorted(examples - linked) == [], "examples that the index does not link"
    assert sorted(linked - examples) == [], "index links with no notebook"
