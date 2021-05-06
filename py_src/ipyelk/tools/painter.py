# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import traitlets as T

from .tool import Tool


class Painter(Tool):
    cssClasses = T.Unicode(default_value="")
    marks = T.List()  # list of ids?
    name = T.Unicode()
