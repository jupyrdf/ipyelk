import warnings
from typing import Any, Dict, Hashable, Iterator, List, Tuple

import pandas as pd
import traitlets as T

from ipyelk import ElementLoader
from ipyelk.elements import ElementMetadata, Label, LabelProperties, Node
from ipyelk.elements import layout_options as opts

attr_label_opts = {
    opts.NodeLabelPlacement.identifier: "H_LEFT V_CENTER INSIDE",
}

name_label_opts = {
    opts.NodeLabelPlacement.identifier: "H_CENTER V_TOP INSIDE",
}


class RowMetadata(ElementMetadata):
    index: Any
    data: Dict


class GroupMetadata(ElementMetadata):
    group: Tuple


class AttrMetadata(ElementMetadata):
    index: Any
    key: str
    value: Any


def groupby(df, by: List[str] = None) -> Iterator[Tuple[List[Hashable], pd.DataFrame]]:
    if not by:
        return [[None, df]]
    else:
        return df.groupby(by=by)


class PandasLoader(ElementLoader):
    root_id: str = T.Unicode(allow_none=True)

    def load(
        self,
        node_data: pd.DataFrame,
        edges: pd.DataFrame = None,
        by: List[str] = None,
        attrs: List[str] = None,
    ):
        root = Node(id=self.root_id)
        nodes: List[Node] = []
        hierarchy: Dict[tuple, Node] = {}
        depth = len(by) if by else 0

        if depth:
            by_col_nulls = [b for b in by if pd.isnull(df[b]).any()]
            if by_col_nulls:
                warnings.warn(
                    "Following `by` columns contain null values. {}".format(
                        by_col_nulls
                    )
                )

        for g, data in groupby(node_data, by=by):
            if depth == 1:
                # if only a single category level pandas groupby returns the value rather than a tuple of values
                g = tuple([g])
            parent = self.get_parent(g, hierarchy, root=root)
            for i, node in data.iterrows():
                n = Node(
                    labels=self.get_labels(node, attrs, index=i),
                    metadata=RowMetadata(
                        index=i,
                        data=node,
                    ),
                )
                nodes.append(parent.add_child(n))
        return super().load(root=root)

    def get_labels(self, node: dict, attrs: List[str], index) -> List[Label]:
        labels = []
        for attr in attrs:
            value = node.get(attr)
            if value:
                labels.append(
                    Label(
                        text=f"{attr} = {value}",
                        layoutOptions=attr_label_opts,
                        properties=LabelProperties(selectable=True),
                        metadata=AttrMetadata(
                            key=attr,
                            value=value,
                            index=index,
                        ),
                    )
                )
        return labels

    def get_title(self, g):
        return Label(text=g[-1])

    def get_parent(self, g: tuple, hierarchy: Dict[Tuple, Node], root: Node):
        if g is None:
            return root
        if g not in hierarchy:
            parent = self.get_parent(g[:-1], hierarchy, root) if len(g) > 1 else root

            hierarchy[g] = parent.add_child(
                Node(
                    labels=[self.get_title(g)],
                    metadata=GroupMetadata(
                        group=g,
                    ),
                )
            )
        return hierarchy[g]
