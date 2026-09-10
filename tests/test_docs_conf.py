# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
"""Regression checks for the ``sphinx-jsonschema`` patch in ``docs/conf.py``."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

CONF_PY = Path(__file__).parent.parent / "docs/conf.py"


def test_docs_conf_description_row(monkeypatch: pytest.MonkeyPatch) -> None:
    """The patched ``_check_description`` must only use real ``WideFormat`` API.

    Regression: ``self._linme`` (a typo for ``self._line``) crashed every
    ``.. jsonschema::`` directive whose schema had a ``description`` on a row.
    """
    pytest.importorskip("sphinx-jsonschema.wide_format")
    # avoid needing the ``pandoc`` binary: the conversion itself is not under test
    monkeypatch.setitem(
        sys.modules,
        "pypandoc",
        SimpleNamespace(convert_text=lambda text, *_, **__: text),
    )
    monkeypatch.delenv("READTHEDOCS", raising=False)

    conf: dict[str, Any] = runpy.run_path(str(CONF_PY))
    conf["setup"](SimpleNamespace())

    wf_cls = __import__("sphinx-jsonschema.wide_format").wide_format.WideFormat
    wf = wf_cls.__new__(wf_cls)
    wf.lineno = 1
    wf.state = SimpleNamespace(document=SimpleNamespace(current_source="test"))

    rows: list[Any] = []
    schema = {"description": "a *row* description", "type": "string"}
    wf._check_description(schema, rows)

    assert "description" not in schema
    assert len(rows) == 1
    (cell,) = rows[0]
    assert "a *row* description" in "\n".join(cell[3])
