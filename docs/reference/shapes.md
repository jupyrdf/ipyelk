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
- If a `LabelShape` sets both `width` and `height`, and neither is 0, the frontend does
  not measure the text of the label.

After each layout, ipyelk writes the laid-out `width` and `height` that come back from
the frontend onto the element, where you can read them. A laid-out size is the output of
a layout, not an input to the next one unless nothing else gives the element a size. The
size that ipyelk serializes as the input to the next layout is, in this order:

1. The `width` or `height` that you assigned to the element, also before the first
   layout. The layout does not forget it: it is sent again after each layout. Assign
   `None` to drop it.
2. The size of the shape. So `node.properties.shape.radius = 20` after a layout changes
   the size of the node at the next layout.
3. The laid-out size, for an element whose shape has no size, or that has no shape.

This rule applies when ipyelk serializes the elements as the input to a layout, which
the `VisibilityPipe` does under `exclude_layout`. Any other serialization, for example
the one that shows the elements in the view after a refresh that runs no layout, or a
plain `model_dump()`, carries the laid-out size. So does a pipeline that you compose
without a `VisibilityPipe`.

A change to a shape's size needs a layout to update the view. After changing the radius
of a node in `diagram.source`, request that layout before refreshing:

```python
from ipyelk.pipes import flows as F

node.properties.shape.radius = 20
diagram.source.record(F.Layout)
diagram.refresh()
```

A bare `diagram.refresh()` does not request a layout after this edit.

The same holds for the size that the frontend measures for a label: if the `LabelShape`
sets `width` but not `height`, the layout gets the `width` of the shape and the measured
`height`, starting with the first layout. A `width` or `height` assigned to a `Label` is
also sent to the layout instead of the measured size, starting with the first layout.

The shape keeps its class and its fields through a layout. The frontend does not change
the `properties` of an element, so ipyelk keeps them, with the shape object, for example
a `Widget` with its widget, and does not replace them with what comes back. A layout can
give a node a size other than the size of its shape, for example a `Circle` node with
children. The `radius` then stays as you set it, and the `width` and `height` of the
node hold the laid-out size.

## Shapes from JSON

When ipyelk loads ELK JSON, the type string of each shape selects its class. ELK JSON
comes back from the frontend after each layout, and `from_elkjson` loads it from a
dictionary. A shape with the type string `node:path` loads as a `Path`, and a shape with
`label:icon` loads as an `Icon`. A shape with no type string loads as the shape class of
its element, for example `NodeShape`. If the type string belongs to another kind of
element, for example `label:icon` on a node, loading raises a `ValidationError`.

`Circle` and `Ellipse` have the same type string, `node:round`. The JSON does not hold
`radius`, `rx` or `ry`, and the renderer draws both shapes from the width and height. So
a `node:round` shape loads as an `Ellipse` with the `width` and `height` of the JSON. A
`node:widget` shape loads as a `Widget` with the widget that has the `model_id` in
`use`. If no open widget has that `model_id`, the shape loads as a `NodeShape` with the
same JSON, and ipyelk warns. This occurs when the widget closed, or when the JSON comes
from another kernel. Only ELK JSON loads in this way: a `node:widget` dictionary in your
own code with no open widget raises a `ValidationError`.

If a shape class of your own sets a new type string, the class adds itself to
`BaseShape.json_classes` when Python defines it. If another class already has that type
string, ipyelk warns, and JSON loads the type string as the new class.

An element, its properties and its shape raise a `ValidationError` for a key that they
do not have, because such a key is usually a typo. For example, `Rect(start="arrow")`
raises, because `start` is a field of `EdgeShape`. ELK JSON can have keys that the
models do not have, so loading ELK JSON ignores them. `from_wire(Node, data)` from
`ipyelk.elements` loads a dictionary in the same way.

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
    :members: dimension, json_classes, loads_from_json
.. autoclass:: ElementShape
.. autoclass:: NodeShape
.. autoclass:: Point
```
