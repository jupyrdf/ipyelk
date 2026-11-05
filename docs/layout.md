# Node size and label placement

A node's `width` and `height` are preferred dimensions when its ELK size constraints
allow growth for labels or ports. To keep a leaf node at a fixed size, set
`NodeSizeConstraints.identifier` to an empty string in that node's `layoutOptions`.
Setting only `width` and `height` does not disable automatic sizing.

This example fixes a node at 80 by 50 layout units and places its label in the center:

```python
from IPython.display import display

from ipyelk import from_element
from ipyelk.elements import Label, Node
from ipyelk.elements.layout_options import NodeLabelPlacement, NodeSizeConstraints

placement = NodeLabelPlacement(horizontal="center", vertical="center")
node = Node(
    id="fixed",
    width=80,
    height=50,
    labels=[
        Label(
            text="Centered",
            layoutOptions={NodeLabelPlacement.identifier: placement.value},
        )
    ],
    layoutOptions={
        NodeSizeConstraints.identifier: "",
        NodeLabelPlacement.identifier: placement.value,
    },
)
root = Node(id="root", children=[node])
diagram = from_element(root)
display(diagram)
```

Set placement on the label as well as the node: `from_element` otherwise supplies a
top-centered default for labels, which takes precedence over the node option. The
placement helper produces `H_CENTER V_CENTER INSIDE`: specify both axes and the inside
placement, rather than relying on a partial ELK option. The wrapper root lets ELK lay
out the fixed node as a child. Label dimensions are measured in the browser; font choice
affects the label's dimensions, but not this fixed node's size.

Fixed dimensions can leave too little space for a long label or many ports. Allow ELK to
size the node when its content must fit: omit the empty constraint override, or use
`NodeSizeConstraints` to choose which content contributes to sizing. The
[ELK node size constraints reference](https://eclipse.dev/elk/reference/options/org-eclipse-elk-nodeSize-constraints.html)
describes those choices.
