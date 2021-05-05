# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

import traitlets as T
from ipywidgets.widgets.trait_types import TypedTuple

from ..elements import (
    Registry,
    VisIndex,
    convert_elkjson,
    exclude_hidden,
    exclude_layout,
    index,
)
from . import flows as F
from .base import Pipe


class VisibilityPipe(Pipe):

    observes = TypedTuple(
        T.Unicode(),
        default_value=(
            F.AnyHidden,
            F.Layout,
        ),
    )

    @T.default("reports")
    def _default_reports(self):
        return (F.Layout,)

    async def run(self):
        if self.outlet is None or self.inlet is None:
            return

        root = self.inlet.value
        # generate an index of hidden elements
        vis_index = VisIndex.from_els(root)

        # Check if any elements are hidden
        if len(vis_index):
            # serialize the elements excluding hidden
            with exclude_hidden, exclude_layout:
                data = root.dict()

            # new root node with slack edges / ports introduced due to hidden
            # elements
            with Registry():
                value = convert_elkjson(data, vis_index)

                for el in index.iter_elements(value):
                    el.id = el.get_id()
            self.outlet.value = value
        else:
            self.outlet.value = self.inlet.value

        return self.outlet
