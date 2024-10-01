# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import sys
from pathlib import Path

from .constants import EXTENSION_NAME

HERE = Path(__file__).parent

IN_TREE = (HERE / f"../_d/share/jupyter/labextensions/{EXTENSION_NAME}").resolve()
IN_PREFIX = Path(sys.prefix) / f"share/jupyter/labextensions/{EXTENSION_NAME}"

__prefix__ = IN_TREE if IN_TREE.exists() else IN_PREFIX

PKG_JSON = __prefix__ / "package.json"

__all__ = ["__prefix__"]
