# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from ..elements import Mark, Node, Registry

# from ..model.model import ElkNode
from ..schema.validator import validate_elk_json
from .abstract_transformer import AbstractTransformer
from .mappings import iter_elements, node_from_elkjson


class ElkJSONTransformer(AbstractTransformer):
    """ Transform data into the form required by the Diagram. """

    _version: str = "v1"

    async def transform(self, data) -> Node:
        """Generate elk json"""
        self.context = Registry()
        root = node_from_elkjson(data)
        self.register_marks(root)
        return root.dict(exclude_none=True)

    def register_marks(self, root: Node):
        for el in iter_elements(root):
            self.register(Mark(element=el, context=self.context))

    @classmethod
    def check(cls, data) -> bool:
        """Check if this transformer can operate on input datatype i.e. data
        version and type.
        """
        return validate_elk_json(data)
