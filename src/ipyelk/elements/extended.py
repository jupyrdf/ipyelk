# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

from typing import Type

from pydantic import (
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from ..util import merge
from . import layout_options as opt
from .elements import Edge, Label, LabelProperties, Node
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
        default=Edge, exclude=True, description="default edge style to apply"
    )

    def __getitem__(self, key):
        if isinstance(key, slice):
            kwargs = {
                "source": key.start,
                "target": key.stop,
                "cls": key.step if is_edge(key.step) else self.get_default_edge(),
            }

            edge = self.add_edge(**kwargs)
            if isinstance(key.step, str):
                edge.labels.append(Label(text=key.step))
            return edge

    def get_default_edge(self) -> Type[Edge]:
        return self.default_edge


class Record(Node):
    """A node whose children are compartments of one shared width.

    Serializing a ``Record`` sets each child's minimum size to ``width`` (cut to
    a whole number) and ``min_height``. A ``min_height`` that is not a whole
    number, such as ``33.7``, raises ``ValueError`` when it is serialized.
    """

    layoutOptions: dict = Field(default_factory=lambda: {**record_opts})
    width: float = Field(
        default=80, description="Width needs to be shared by all children "
    )
    min_height: float = Field(
        default=20,
        exclude=True,
        description="Minimum height of a compartment, a whole number",
    )

    @model_serializer(mode="wrap")
    def serialize_element(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ):
        # TODO(#209): size the min width from the widest label or child
        # the strings the option widgets would make: a widget built on every dump
        # is never closed
        constraints = "NODE_LABELS PORTS PORT_LABELS MINIMUM_SIZE"
        if not float(self.min_height).is_integer():
            # the `Int` trait of the old `NodeSizeMinimum` widget rejected it too
            msg = f"Record.min_height must be a whole number, not {self.min_height!r}"
            raise ValueError(msg)
        minimum = f"({int(self.width)}, {int(self.min_height)})"
        size = {
            opt.NodeSizeConstraints.identifier: constraints,
            opt.NodeSizeMinimum.identifier: minimum,
        }
        for child in self.children:
            child.layoutOptions = merge(size, child.layoutOptions)
        return super().serialize_element(handler, info)


class Compartment(Node):
    bullet_shape: Icon | None = Field(None, exclude=True)

    def make_labels(
        self, headings: list[str] | None = None, content: list[str] | None = None
    ) -> Compartment:
        if headings is None:
            headings = []
        if content is None:
            content = []
        bullet_label = []
        if self.bullet_shape:
            bullet_label = [
                Label(
                    properties=LabelProperties(
                        shape=self.bullet_shape, selectable=True
                    ),
                    layoutOptions=bullet_opts,
                )
            ]
        if headings and not content:
            heading_label_opts = center_label_opts
            heading_cls = "compartment_title"
        else:
            heading_label_opts = top_center_label_opts
            heading_cls = "heading"
        heading = [
            Label(text=text, layoutOptions=heading_label_opts).add_class(
                f"{heading_cls}_{i + 1}"
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
