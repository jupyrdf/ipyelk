
from ipyelk.elements.mark_factory import Mark
import traitlets as T

from typing import Optional, Dict

from ..tools import Tool
from ..elements import Node, index, layout_options as opt
from ..pipes import MarkElementWidget
from .loader import Loader


class ElementLoader(Loader):
    def load(self, root:Node) -> MarkElementWidget:

        return MarkElementWidget(
            value=self.apply_layout_defaults(root),
        )
