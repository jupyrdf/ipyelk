# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from typing import Tuple

import traitlets as T

from ..pipes import BrowserTextSizer, ElkJS, Pipeline, VisibilityPipe
from ..tools import Selection, Tool


class DefaultFlow(Pipeline):
    vis_pipe: VisibilityPipe = T.Instance(VisibilityPipe, kw={})

    @T.default("pipes")
    def _default_pipes(self):
        return [
            BrowserTextSizer(),
            self.vis_pipe,
            ElkJS(),
            # SprottyViewer(),
            # Downselect(),
            # MiniSprottyViewer(),
        ]

    def link_selection(self, selection: Selection):
        selection.tee = self
        self.vis_pipe.collapser.selection = selection
        return self

    def get_tools(self) -> Tuple[Tool]:
        return (self.vis_pipe.collapser,)
