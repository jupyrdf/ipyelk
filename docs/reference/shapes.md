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
`use` its own meaning, as the API section below shows. For some shapes, `use` holds a
symbol identifier. A symbol is a drawing that you define once with `Symbol` and add to
the `symbols` of the diagram. The symbol identifier is the `identifier` of that
`Symbol`. If no symbol has the identifier, a port draws a rectangle and a label draws
its text. A `Use` node and an edge end draw nothing. Typed fields in place of the `use`
string are planned in [#148](https://github.com/jupyrdf/ipyelk/issues/148).

```{warning}
The frontend inserts the markup of `SVG`, `ForeignObject` and `HTML` into the page
without changes. Put only markup from a source that you trust in `use`.
```

## Width and height

The `width` and `height` of a shape are a size in pixels. If the element has no `width`
or `height` of its own, the element serializes the size of its shape. The layout can
then change the size of the element. The laid-out size is the size of the element after
the layout. The renderers use it as follows:

- Most renderers draw the shape at the laid-out size.
- The `node:round` renderer of `Circle` and `Ellipse` draws an ellipse. Its radii are
  half the laid-out width and height. If `x` and `y` are not set, the ellipse is at the
  center of the node.
- `Path` and `SVG` draw their markup at its own coordinates. The renderer does not scale
  it.
- A parent label places its icon and its text with the `width` and `height` of the
  `Icon` shape, if they are set. It draws the icon at the laid-out size.
- If a `LabelShape` sets both `width` and `height`, the frontend does not measure the
  text of the label.

These rules apply until the first layout. After each layout, ipyelk copies the
`properties`, `width` and `height` that come back from the frontend onto the element.
The element then has the laid-out size as its own size, so a later change to the size of
its shape has no effect.

The shape also loses its subclass. For example, a `Circle` becomes a `NodeShape`, and an
`Icon` becomes a `LabelShape`. After that, `node.properties.shape.radius = 20` raises a
`ValueError`. To change the shape after a layout, assign a new shape and set the `width`
and `height` of the element to `None`.

## The shapes

The example column links to a notebook that runs in your browser.

| Class                                             | `type` string        | Example                                                                                                                                                                      |
| ------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| {py:class}`~ipyelk.elements.shapes.Rect`          | `node`               | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Circle`        | `node:round`         | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Ellipse`       | `node:round`         | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Diamond`       | `node:diamond`       | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Comment`       | `node:comment`       | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Path`          | `node:path`          | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>   |
| {py:class}`~ipyelk.elements.shapes.SVG`           | `node:svg`           | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=11_Logic_Gates.ipynb">11_Logic_Gates</a>     |
| {py:class}`~ipyelk.elements.shapes.Use`           | `node:use`           | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>, <a href="../_static/lab/index.html?path=11_Logic_Gates.ipynb">11_Logic_Gates</a>         |
| {py:class}`~ipyelk.elements.shapes.Image`         | `node:image`         | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.ForeignObject` | `node:foreignobject` | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.HTML`          | `node:html`          | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.Widget`        | `node:widget`        | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>, <a href="../_static/lab/index.html?path=15_Nesting_Plots.ipynb">15_Nesting_Plots</a> |
| {py:class}`~ipyelk.elements.shapes.PortShape`     | `port`               | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>                                                                                           |
| {py:class}`~ipyelk.elements.shapes.LabelShape`    | `label`              |                                                                                                                                                                              |
| {py:class}`~ipyelk.elements.shapes.Icon`          | `label:icon`         | <a href="../_static/lab/index.html?path=12_Node_Menagerie.ipynb">12_Node_Menagerie</a>                                                                                       |
| {py:class}`~ipyelk.elements.shapes.EdgeShape`     | `edge`               | <a href="../_static/lab/index.html?path=10_Diagram_Defs.ipynb">10_Diagram_Defs</a>                                                                                           |

## Section dividers in a node

To divide a node into sections, use labels, not a node shape. Set `separator=True` in
the `LabelProperties` of the first label of each section. The frontend draws a line
across the full width of the node above each of these labels. `separatorGap` sets the
distance in pixels between the line and the label. Labels above the first line, for
example a title, are optional. The frontend also has an older `node:compartment`
renderer, which has no shape class.

## API

### Node shapes

```{eval-rst}
.. currentmodule:: ipyelk.elements.shapes

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

### Symbols

```{eval-rst}
.. currentmodule:: ipyelk.elements
.. autoclass:: Symbol
.. autoclass:: EndpointSymbol
.. autoclass:: SymbolSpec
    :members: add, merge
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
