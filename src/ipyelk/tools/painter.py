# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import traitlets as T

from .tool import Tool


class Painter(Tool):
    cssClasses = T.Unicode(default_value="")
    marks = T.List[object](default_value=[])
    name = T.Unicode()
