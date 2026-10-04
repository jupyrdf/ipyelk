# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
import asyncio
import os

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..constants import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from . import flows as F
from .base import SyncedPipe
from .util import browser_roundtrip


class ElkJS(SyncedPipe):
    """JupyterLab widget for calling `elkjs <https://github.com/kieler/elkjs>`_
    layout given a valid elkjson dictionary
    """

    _model_name = T.Unicode("ELKLayoutModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)

    observes: tuple[str, ...] = TypedTuple(
        T.Unicode(),
        default_value=(F.Anythinglayout,),
    )
    reports: tuple[str, ...] = TypedTuple(T.Unicode(), default_value=(F.Layout,))
    timeout = T.Float(
        default_value=30.0,
        help=(
            "Seconds to wait for the browser to return a layout before giving up; "
            "0 waits forever (the request is re-sent with backoff until a frontend answers)"
        ),
    )

    async def run(self):
        # watch once
        # signal to browser (re-sending until a frontend answers) and wait
        # for done, browser error, or deadline
        try:
            await browser_roundtrip(self, timeout=self.timeout or None)
        except asyncio.TimeoutError:
            if not os.environ.get("IPYELK_NO_BROWSER"):
                raise
            # no frontend (`nbconvert --execute`): nothing can lay the graph
            # out, so pass it on unlaid-out and let the run succeed
            self.outlet.value = self.inlet.value
        else:
            self.outlet.persist()
