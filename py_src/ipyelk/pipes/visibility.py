# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.

from ..elements import (
    Registry,
    VisIndex,
    exclude_hidden,
    exclude_layout,
    from_elkjson,
    index,
)
from .base import Pipe


class VisibilityPipe(Pipe):
    async def run(self):
        """Go measure some dom"""
        if self.outlet is None or self.inlet is None:
            return

        root = self.inlet.value
        # generate an index of hidden elements
        vis_index = VisIndex.from_els(root)

        # TODO check if a change occurred
        if len(vis_index):
            # serialize the elements excluding hidden
            with exclude_hidden, exclude_layout:
                data = root.dict()

            # new root node with slack edges / ports introduced due to hidden
            # elements
            with Registry():
                value = from_elkjson(data, vis_index)

                for el in index.iter_elements(value):
                    el.id = el.get_id()
            self.outlet.value = value
        else:
            self.outlet.value = self.inlet.value

        return self.outlet
