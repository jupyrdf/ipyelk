# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ..diagram import Diagram
from ..elements import Node
from ..pipes import MarkElementWidget
from .loader import Loader


class ElementLoader(Loader):
    def load(self, root: Node) -> MarkElementWidget:

        return MarkElementWidget(
            value=self.apply_layout_defaults(root),
        )


def from_element(root: Node, **kwargs):
    diagram = Diagram(source=ElementLoader().load(root=root), **kwargs)
    return diagram
