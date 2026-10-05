# Shapes

A shape tells the frontend how to draw one element of a diagram. The frontend is the
ipyelk JupyterLab extension that draws the diagram in the browser. An element is a node,
a port, a label or an edge. The frontend draws most shapes in one SVG element, the
diagram SVG.

## How an element gets its shape

Each element has a `properties` object, and the shape is the `shape` field of that
object. Each kind of element has its own properties class:

| Element | Properties class  | Shape classes                                  |
| ------- | ----------------- | ---------------------------------------------- |
| node    | `NodeProperties`  | `NodeShape` and its subclasses, such as `Rect` |
| port    | `PortProperties`  | `PortShape`                                    |
| label   | `LabelProperties` | `LabelShape` and `Icon`                        |
| edge    | `EdgeProperties`  | `EdgeShape`                                    |

```python
from ipyelk.elements import Node, NodeProperties, shapes

node = Node(properties=NodeProperties(shape=shapes.Circle(radius=20)))
```

The `type` field of a shape holds the type string, for example `node:round`. The
frontend uses the type string to select the renderer. A renderer is the frontend view
that draws one kind of shape. If an element has no shape, or its shape has no `type`,
the frontend uses the default renderer for the element. The default renderers draw a
rectangle for a node or a port, the text for a label and a line for an edge.

## The `use` field

Most shapes hold their data in the `use` field, which is a string. Each shape gives
`use` its own meaning, as the table below shows. For some shapes, `use` holds a symbol
identifier. A symbol is a drawing that you define once with `Symbol` and add to the
`symbols` of the diagram. The symbol identifier is the `identifier` of that `Symbol`.
Typed fields in place of the `use` string are planned in
[#148](https://github.com/jupyrdf/ipyelk/issues/148).

## Width and height

The `width` and `height` of a shape are a size in pixels. If the element has no `width`
or `height` of its own, the element uses the value of its shape. The layout can then
change the size of the element. Most renderers draw the shape at the size that the
layout gives.

## The shapes

The example column links to a notebook that runs in your browser.

| Class           | `type` string        | What `use` holds                                     | Other fields         | Example                                                                                                                                                                      |
| --------------- | -------------------- | ---------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Rect`          | `node`               | Nothing                                              | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Circle`        | `node:round`         | Nothing                                              | `radius`, `x`, `y`   | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Ellipse`       | `node:round`         | Nothing                                              | `rx`, `ry`, `x`, `y` | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Diamond`       | `node:diamond`       | Nothing                                              | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Comment`       | `node:comment`       | The size of the corner notch in pixels, as a string  | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Path`          | `node:path`          | SVG path data                                        | None                 | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>   |
| `SVG`           | `node:svg`           | SVG markup                                           | `x`, `y`             | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=11_Logic_Gates.ipynb">11_Logic_Gates</a>     |
| `Use`           | `node:use`           | A symbol identifier                                  | `width`, `height`    | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>, <a href="../_static/lab/index.html?path=11_Logic_Gates.ipynb">11_Logic_Gates</a>         |
| `Image`         | `node:image`         | The URL of an image                                  | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `ForeignObject` | `node:foreignobject` | HTML markup, drawn in the diagram SVG                | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `HTML`          | `node:html`          | HTML markup, drawn above the diagram SVG             | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Widget`        | `node:widget`        | The `model_id` of `widget`, written by serialization | `widget`, `delay`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=15_Nesting_Plots.ipynb">15_Nesting_Plots</a> |
| `PortShape`     | `port`               | A symbol identifier, or `None` for a rectangle       | `width`, `height`    | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>                                                                                           |
| `LabelShape`    | `label`              | A symbol identifier, or `None` for the text          | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `Icon`          | `label:icon`         | A symbol identifier (required)                       | `width`, `height`    | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| `EdgeShape`     | `edge`               | No `use` field                                       | `start`, `end`       | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>                                                                                           |

`Circle` and `Ellipse` share the `node:round` renderer. `EdgeShape.start` and
`EdgeShape.end` are symbol identifiers. The frontend draws them at the two ends of the
edge, for example as arrowheads.

```{warning}
The frontend inserts the markup of `SVG`, `ForeignObject` and `HTML` into the page
without changes. Put only markup from a source that you trust in `use`.
```

## Section dividers in a node

To divide a node into sections, use labels, not a node shape. Give the node a title
label first. Then set `separator=True` in the `LabelProperties` of the first label of
each section. The frontend draws a line across the full width of the node above each of
these labels. `separatorGap` sets the distance in pixels between the line and the label.
The frontend also has an older `node:compartment` renderer, which has no shape class.

## API

### Node shapes

```{eval-rst}
.. currentmodule:: ipyelk.elements.shapes
.. automodule:: ipyelk.elements.shapes

.. autoclass:: Rect
.. autoclass:: Circle
.. autoclass:: Ellipse
.. autoclass:: Diamond
.. autoclass:: Comment
.. autoclass:: Path
    :members: from_list
.. autoclass:: SVG
.. autoclass:: Use
.. autoclass:: Image
.. autoclass:: ForeignObject
.. autoclass:: HTML
.. autoclass:: Widget
```

### Port, label and edge shapes

```{eval-rst}
.. currentmodule:: ipyelk.elements.shapes
.. autoclass:: PortShape
.. autoclass:: LabelShape
.. autoclass:: Icon
.. autoclass:: EdgeShape
```

### Base classes

```{eval-rst}
.. currentmodule:: ipyelk.elements.shapes
.. autoclass:: BaseShape
    :members: dimension
.. autoclass:: ElementShape
.. autoclass:: NodeShape
.. autoclass:: Point
```
