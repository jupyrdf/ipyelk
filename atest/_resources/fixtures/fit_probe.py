"""Show a laid-out diagram that fits each view itself, for the gh-245 robot test."""
# Copyright (c) 2024 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import json
import sys

import ipywidgets as W
from IPython.display import display

from ipyelk.diagram import SprottyViewer

#: padding of the first-layout fit, in diagram units; the robot test allows for it
PADDING = 10


def view(**kwargs):
    """A viewer that fits each view after its first layout."""
    return SprottyViewer(fit_on_first_layout=True, fit_padding=PADDING, **kwargs)


class Probe:
    """Hold an undisplayed diagram until its first layout, then show it twice."""

    def __init__(self, diagram):
        self.diagram = diagram
        self.accordion = None

    def report(self, token):
        """Print ``token`` and whether the diagram's first layout is done."""
        value = self.diagram.view.source and self.diagram.view.source.value
        children = [] if value is None else value.children
        laid_out = any((child.width or 0) > 0 for child in children)
        sys.stdout.write(f"{token} {json.dumps({'laid_out': laid_out})}\n")

    def show(self):
        """Display one view, and one in a collapsed accordion (hidden)."""
        display(self.diagram)
        self.accordion = W.Accordion(children=[self.diagram], selected_index=None)
        self.accordion.set_title(0, "fit-on-first-layout")
        display(self.accordion)
