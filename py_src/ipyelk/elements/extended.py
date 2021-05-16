# Copyright (c) 2021 Dane Freeman.
# Distributed under the terms of the Modified BSD License.
from typing import Dict, List, Optional, Type

from pydantic import Field

from ..util import merge
from . import layout_options as opt
from .elements import Edge, Label, LabelProperties, Node, merge_excluded
from .shapes import Icon

record_opts = opt.OptionsWidget(
    options=[
        #         opt.LayoutAlgorithm(value=ELKRectanglePacking.identifier),
        opt.HierarchyHandling(),
        opt.Padding(left=0, right=0, bottom=0, top=0),
        opt.NodeSpacing(spacing=0),
        opt.EdgeNodeSpacing(spacing=0),
        opt.AspectRatio(ratio=100),
        opt.ExpandNodes(activate=True),
        opt.NodeLabelPlacement(horizontal="center", vertical="center"),
        opt.NodeSizeConstraints(),
        opt.ComponentsSpacing(spacing=0),
        opt.NodeSpacing(spacing=0),
    ]
).value


content_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="left", vertical="center")]
).value

top_center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="top")]
).value

center_label_opts = opt.OptionsWidget(
    options=[opt.NodeLabelPlacement(horizontal="center", vertical="center")]
).value

bullet_opts = opt.OptionsWidget(
    options=[
        opt.LabelSpacing(spacing=4),
    ]
).value

compart_opts = opt.OptionsWidget(
    options=[
        opt.NodeSizeConstraints(),
    ]
).value


def is_edge(edge) -> bool:
    try:
        return issubclass(edge, Edge)
    except Exception:
        return False


class Partition(Node):
    default_edge: Type[Edge] = Field(
        default=Edge, description="default edge style to apply"
    )

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = merge_excluded(Node, "default_edge")

    def __getitem__(self, key):
        if isinstance(key, slice):
            kwargs = {
                "source": key.start,
                "target": key.stop,
                "cls": key.step if is_edge(key.step) else self.default_edge,
            }

            edge = self.add_edge(**kwargs)
            if isinstance(key.step, str):
                edge.labels.append(Label(text=key.step))
            return edge


class Record(Node):
    layoutOptions: Dict = Field(default_factory=lambda: {**record_opts})
    width: float = Field(
        default=80, description="Width needs to be shared by all children "
    )
    min_height: float = Field(default=20, description="Minimum height of a compartment")

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = merge_excluded(Node, "min_height")

    def dict(self, **kwargs):
        # TODO need ability to resize the min width based on label/child max width
        for child in self.children:
            child.layoutOptions = merge(
                opt.OptionsWidget(
                    options=[
                        opt.NodeSizeConstraints(),
                        opt.NodeSizeMinimum(
                            width=int(self.width), height=self.min_height
                        ),
                    ]
                ).value,
                child.layoutOptions,
            )
        return super().dict(**kwargs)


class Compartment(Record):
    bullet_shape: Optional[Icon] = None

    class Config:
        copy_on_model_validation = False

        # non-pydantic configs
        excluded = merge_excluded(Node, "headings", "content", "bullet_shape")

    def make_labels(
        self, headings: List[str] = None, content: List[str] = None
    ) -> "Compartment":
        if headings is None:
            headings = []
        if content is None:
            content = []
        bullet_label = []
        if self.bullet_shape:
            bullet_label = Label(
                properties=LabelProperties(shape=self.bullet_shape),
                layoutOptions=bullet_opts,
                selectable=True,
            )
        if headings and not content:
            heading_label_opts = center_label_opts
            heading_cls = "compartment_title"
        else:
            heading_label_opts = top_center_label_opts
            heading_cls = "heading"
        heading = [
            Label(text=text, layoutOptions=heading_label_opts).add_class(
                f"{heading_cls}_{i+1}"
            )
            for i, text in enumerate(headings)
        ]
        content = [
            Label(
                text=text,
                layoutOptions=content_label_opts,
                labels=bullet_label,
                properties=LabelProperties(selectable=True),
            )
            for text in content
        ]
        self.labels = [*heading, *content]
        return self
