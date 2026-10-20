# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    VisIndex,
    convert_elkjson,
    exclude_hidden,
    exclude_layout,
)
from . import flows as F
from .base import Pipe


class VisibilityPipe(Pipe):
    #: the projection is a copy of the whole tree, so any change makes it stale
    #: (#246); a later stage keeps it only while nothing changed (#231)
    observes = TypedTuple(T.Unicode(), default_value=(".*",))

    @T.default("reports")
    def _default_reports(self):
        return (F.Layout,)

    async def run(self):
        if self.outlet is None or self.inlet is None:
            return None

        root = self.inlet.index.root
        # generate an index of hidden elements
        vis_index = VisIndex.from_els(root)

        # clear old slack CSS classes from elements
        vis_index.clear_slack(root)

        # serialize the elements excluding hidden
        with exclude_hidden, exclude_layout:
            data = root.model_dump()

        # new root node with slack edges / ports introduced due to hidden
        # elements; every element of ``data`` has its wire id, so no id is minted
        value = convert_elkjson(data, vis_index)
        # the browser can select a slack port: resolve it to its hidden element
        self.inlet.index.document.slack = dict(vis_index.slack_ports)
        self.outlet.value = value

        return self.outlet
