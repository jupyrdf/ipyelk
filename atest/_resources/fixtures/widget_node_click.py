"""Build a diagram with one widget node, an icon button, for a robot test."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import ipywidgets as W
import networkx as nx

import ipyelk
from ipyelk.elements import shapes
from ipyelk.loaders import NXLoader


def app():
    """Return a diagram whose only node shows a button with an icon."""
    button = W.Button(icon="plus", description="", layout={"width": "60px"})
    g = nx.Graph()
    g.add_node(
        "button_node",
        properties={"shape": shapes.Widget(widget=button).model_dump()},
        width=80,
        height=40,
    )
    return ipyelk.Diagram(
        source=NXLoader(default_node_opts=None).load(graph=g),
        layout={"height": "300px"},
    )
