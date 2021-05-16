# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import traitlets as T

from ..pipes import BrowserTextSizer, ElkJS, Pipeline, ValidationPipe, VisibilityPipe


class DefaultFlow(Pipeline):
    @T.default("pipes")
    def _default_pipes(self):
        return [
            ValidationPipe(),
            BrowserTextSizer(),
            VisibilityPipe(),
            ElkJS(),
        ]
