# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import traitlets as T

from .tool import Tool


class Painter(Tool):
    cssClasses = T.Unicode(default_value="")
    marks: list[object] = T.List(default_value=[])  # type: ignore[assignment]
    name = T.Unicode()
