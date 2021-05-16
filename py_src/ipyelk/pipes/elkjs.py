# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from .._version import EXTENSION_NAME, EXTENSION_SPEC_VERSION
from . import flows as F
from .base import SyncedPipe
from .util import wait_for_change


class ElkJS(SyncedPipe):
    """Jupyterlab widget for calling `elkjs <https://github.com/kieler/elkjs>`_
    layout given a valid elkjson dictionary"""

    _model_name = T.Unicode("ELKLayoutModel").tag(sync=True)
    _model_module = T.Unicode(EXTENSION_NAME).tag(sync=True)
    _model_module_version = T.Unicode(EXTENSION_SPEC_VERSION).tag(sync=True)
    _view_module = T.Unicode(EXTENSION_NAME).tag(sync=True)

    observes = TypedTuple(T.Unicode(), default_value=(F.Anythinglayout,))
    reports = TypedTuple(T.Unicode(), default_value=(F.Layout,))

    async def run(self):
        # watch once
        if self.outlet is None:
            return

        # signal to browser and wait for done
        future_value = wait_for_change(self.outlet, "value")
        self.send({"action": "run"})

        # wait to return until
        await future_value
        self.outlet.persist()
