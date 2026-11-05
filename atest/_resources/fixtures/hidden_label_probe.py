"""Exercise initially hidden and edited hidden labels in the gh-248 browser test."""
# Copyright (c) 2026 ipyelk contributors.
# Distributed under the terms of the Modified BSD License.

import json
import sys

from IPython.display import display

from ipyelk import Diagram
from ipyelk.elements import Label, Node, NodeProperties
from ipyelk.pipes import MarkElementWidget
from ipyelk.pipes import flows as F


class Probe:
    """Keep the same label through reveal, collapse, hidden edit, and reveal."""

    def __init__(self):
        self.label = Label(text="Initially hidden label")
        self.child = Node(labels=[self.label], properties=NodeProperties(hidden=True))
        root = Node(children=[Node(children=[self.child])])
        self.diagram = Diagram(source=MarkElementWidget(value=root))
        display(self.diagram)

    async def reveal(self):
        """Reveal and wait for the real sizing and layout roundtrips."""
        self.child.properties.hidden = False
        self.diagram.source.record(F.Node.hidden)
        await self.diagram.refresh()

    async def edit_hidden(self):
        """Hide the measured label, then edit it while it cannot be measured."""
        self.child.properties.hidden = True
        self.diagram.source.record(F.Node.hidden)
        await self.diagram.refresh()
        self.label.text = "A substantially longer hidden label after its text changed"
        self.diagram.source.record(F.Text.text)
        await self.diagram.refresh()

    def report(self, token):
        """Report the kernel's measured width and text for a browser assertion."""
        error = self.diagram.pipe.status.exception
        assert error is None, str(error)
        state = {"text": self.label.text, "width": self.label.width}
        sys.stdout.write(f"{token} {json.dumps(state)}\n")
