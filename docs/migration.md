# Migrating from ipyelk 2.x to 3.0

This page is for you if a notebook or a library of yours uses `ipyelk` 2.x. It tells you
how to change that code for `ipyelk` 3.0. Each section describes one breaking change. A
breaking change is a change after which some 2.x code fails or behaves differently.

Each section tells you:

- what changed
- whose code the change affects
- the 2.x code and the 3.0 code
- the error or the symptom that the 2.x code shows on 3.0
- the pull request that made the change

The {doc}`changelog` lists every change, including the changes that do not break 2.x
code.

## Find the changes that affect you

Do these steps before you change your code:

1. Search your code for the removed names in the table in
   {ref}`migration-removed-names`. The table lists the names that raise
   `DeprecatedAPIError` or `DeprecatedImportError`.
2. Run your notebooks and your tests with `ipyelk` 3.0.
3. If you see `DeprecatedAPIError` or `DeprecatedImportError`, read the message. The
   message names the replacement.
4. If you see a `DeprecationWarning`, read the message. The message names the
   replacement. The table in {ref}`migration-deprecated-names` lists the deprecated
   names.
5. Read the sections about changes that do not raise an error:
   - {ref}`migration-unbound`
   - {ref}`migration-callback-argument`
   - {ref}`migration-record-reports`
   - {ref}`migration-hover-leave`
   - {ref}`migration-selection-ids`
   - {ref}`migration-option-ids`
   - {ref}`migration-layout-options`
   - {ref}`migration-shape-classes`
   - {ref}`migration-wrapping-horizontal`
   - {ref}`migration-label-size`
   - {ref}`migration-index-without-id`
   - {ref}`migration-slack-id`
   - {ref}`migration-value-sync`

(migration-removed-names)=

## The errors for removed names

A removed name is an attribute, a constructor keyword or a module-level name that 3.0
deleted. 3.0 has no alias and no deprecation warning for a removed name. Instead,
`ipyelk` raises an error when your code uses a removed name. The message of the error
tells you why the name was removed and what to use instead. Every 3.x release keeps
these errors.

`ipyelk` raises one of two errors:

- `ipyelk.exceptions.DeprecatedAPIError` for a removed attribute or constructor keyword.
  It is a subclass of `AttributeError`. Thus `hasattr()` returns `False` for a removed
  attribute, and `getattr(obj, name, default)` returns the default.
- `ipyelk.exceptions.DeprecatedImportError` for a removed module or module-level name.
  It is a subclass of `ImportError`. Thus `from ipyelk.tools import Zoom` shows the
  message, not only "cannot import name".

The two errors have the same base class, `ipyelk.exceptions.DeprecatedAPI`. One
`except DeprecatedAPI` clause catches both errors.

```python
# 2.x
from ipyelk.tools import Painter

Painter(cssClasses="highlight")
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Painter.cssClasses was removed in ipyelk 3.0: it was an unfinished placeholder that painted nothing. Use painter.paint(ids, *css_classes) / painter.styles (id -> classes applied in the view only). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
from ipyelk.exceptions import DeprecatedAPI
from ipyelk.tools import Hover

print(hasattr(Hover(), "ids"))
try:
    from ipyelk.tools import Zoom
except DeprecatedAPI as error:
    print(type(error).__name__)
```

This table lists the removed names that raise `DeprecatedAPIError` or
`DeprecatedImportError`. Some sections of this page describe other removed names, which
raise no error or a different error. The last column of the table links to the section
that tells you what to use instead.

| Removed name                                                                                        | Error                   | Section                           |
| --------------------------------------------------------------------------------------------------- | ----------------------- | --------------------------------- |
| `Tool.handler`                                                                                      | `DeprecatedAPIError`    | {ref}`migration-trigger`          |
| `ToolButton.handler`, `ToolButton(handler=...)`                                                     | `DeprecatedAPIError`    | {ref}`migration-on-click`         |
| `Tool.on_run`                                                                                       | `DeprecatedAPIError`    | {ref}`migration-on-start-on-done` |
| assigning `Tool.on_start` or `Tool.on_done`                                                         | `DeprecatedAPIError`    | {ref}`migration-on-start-on-done` |
| `Tool.disable`                                                                                      | `DeprecatedAPIError`    | {ref}`migration-disabled`         |
| `Hover.ids`                                                                                         | `DeprecatedAPIError`    | {ref}`migration-hovered-id`       |
| `Viewer.zoom`, `Viewer.pan`, `Viewer.viewed`                                                        | `DeprecatedAPIError`    | {ref}`migration-viewport`         |
| `Painter.cssClasses`, `Painter.marks`, `Painter.name`                                               | `DeprecatedAPIError`    | {ref}`migration-painter`          |
| `ipyelk.tools.Zoom`, `ipyelk.tools.Pan`                                                             | `DeprecatedImportError` | {ref}`migration-zoom-pan-import`  |
| `ipyelk.tools.contol_overlay`                                                                       | `DeprecatedImportError` | {ref}`migration-control-module`   |
| `ipyelk.elements.layout_options.Draw2DLayout`, `ipyelk.elements.layout_options.layout.Draw2DLayout` | `DeprecatedImportError` | {ref}`migration-draw2d`           |
| `ipyelk.pipes.mappings`                                                                             | `DeprecatedImportError` | {ref}`migration-mappings`         |
| `ipyelk.elements.Mark`, `ipyelk.elements.MarkFactory`                                               | `DeprecatedImportError` | {ref}`migration-mark-factory`     |
| `ipyelk.elements.mark_factory`                                                                      | `DeprecatedImportError` | {ref}`migration-mark-factory`     |
| `MarkIndex.comm`, `MarkIndex.close`                                                                 | `DeprecatedAPIError`    | {ref}`migration-markindex-widget` |
| `MarkElementWidget.layout`                                                                          | `DeprecatedAPIError`    | {ref}`migration-markindex-widget` |

(migration-deprecated-names)=

## The warnings for deprecated names

A deprecated name is a name that worked in 2.x and still works in 3.x. When your code
uses a deprecated name, `ipyelk` shows a `DeprecationWarning`. The message names the
replacement. `ipyelk` 4.0 removes `Registry` and `MarkIndex.context`.

| Deprecated name     | Warning              | Section                           |
| ------------------- | -------------------- | --------------------------------- |
| `Registry`          | `DeprecationWarning` | {ref}`migration-document`         |
| `MarkIndex.context` | `DeprecationWarning` | {ref}`migration-markindex-context` |
| `LabelPortSpacing`  | `DeprecationWarning` | {ref}`migration-label-port`       |

## Tools

A tool is an object of the class `ipyelk.tools.Tool` or of one of its subclasses. Tools
control a diagram: `Selection`, `Hover`, `FitTool` and `ToggleCollapsedTool` are tools.

### Tool invocation and lifecycle names

In 2.x, some tool names had more than one role. In 3.0, each name has one role. The
sections below describe each name. The changes are in [#157].

The examples in these sections use this tool:

```python
# both versions: a tool that prints when it runs
from ipyelk.tools import Tool


class Hello(Tool):
    async def run(self):
        print("hello")


tool = Hello()
```

(migration-trigger)=

#### Request a run with `trigger()`

A run is one execution of the `run()` method of a tool. `Tool.trigger()` requests a run.
A call to `trigger()` is a request. `trigger()` cancels a run that did not finish,
schedules `run()`, and returns the `asyncio.Task`. `Tool.handler` is removed.

This change affects code that calls `tool.handler()` or passes `tool.handler` as a
callback. The change is in [#157].

```python
# 2.x
tool.handler()
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.handler was removed in ipyelk 3.0. It was three different things (the execution method, ToolButton's click callback trait, and SetTool's trait observer). Call tool.trigger() to request execution; pass ToolButton(on_click=callback) for a button callback (called as callback(tool)).
```

```python
# 3.0
import ipywidgets as W

button = W.Button(description="Hello")
button.on_click(tool.trigger)  # trigger() ignores the button argument
await tool.trigger()
```

`trigger()` raises `NotImplementedError` for a tool that has no `run()`. In 2.x, the run
failed later, inside the task. `Selection`, `Hover` and `ToolButton` have no `run()`.

```python
# 3.0
from ipyelk.tools import Selection

try:
    Selection().trigger()
except NotImplementedError as error:
    print(error)
```

(migration-on-click)=

#### Give a button its callback with `on_click`

`ToolButton.on_click` replaces the `handler` trait of `ToolButton`. `ToolButton` calls
`on_click(tool)` with the tool as its argument. In 2.x, `ToolButton` called `handler()`
with no argument. `FitTool` and `CenterTool` are subclasses of `ToolButton`.

This change affects code that makes a `ToolButton`, a `FitTool` or a `CenterTool` with
`handler=`, or that sets `handler` on one of them. The change is in [#157].

```python
# both versions
from ipyelk import Diagram
from ipyelk.tools import FitTool

view = Diagram().view
```

```python
# 2.x
FitTool(handler=lambda: view.fit())
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.handler was removed in ipyelk 3.0. It was three different things (the execution method, ToolButton's click callback trait, and SetTool's trait observer). Call tool.trigger() to request execution; pass ToolButton(on_click=callback) for a button callback (called as callback(tool)).
```

```python
# 3.0
fit = FitTool(on_click=lambda tool: view.fit())
fit.ui.click()
```

(migration-on-start-on-done)=

#### Register `on_start` and `on_done` callbacks

`Tool.on_start(callback)` replaces `Tool.on_run(callback)`. `Tool.on_done(callback)` is
now a method that registers a callback. In 2.x, `on_done` was a trait that held one
callback.

- An `on_start` callback fires when the run starts. In 2.x, an `on_run` callback fired
  after a successful run, in spite of its name.
- An `on_done` callback fires only after a successful run. It does not fire when the run
  fails, when a newer request cancels it, or when `trigger()` rejects the request.
- A tool can have more than one `on_start` callback and more than one `on_done`
  callback. The `Diagram` that owns a tool registers its `refresh()` method as an
  `on_done` callback. `remove=True` removes a callback.
- Each callback receives the tool as its argument.

This change affects code that registers `on_run` callbacks or assigns `on_done`. If a
2.x `on_run` callback must see the result of the run, register it with `on_done` in 3.0.
The change is in [#157].

```python
# 2.x
tool.on_run(lambda tool: print("ran"))
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.on_run was removed in ipyelk 3.0. Despite its name, on_run callbacks ran AFTER a successful run, not when the run started, so the name was ambiguous. Register tool.on_start(callback) for the actual start of the work, or tool.on_done(callback) for success only (both are called as callback(tool); on_done never fires on failure, cancellation, or a rejected trigger). No forwarding: this error is raised throughout 3.x.
```

```python
# 2.x
tool.on_done = lambda: print("done")
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.on_done is a registration method in ipyelk 3.0, not an assignable callable: a single slot let one assignment silently replace another listener's callback (the Diagram registers its own refresh on on_done). Register tool.on_done(callback) (called as callback(tool); remove=True unregisters). This error is raised throughout 3.x.
```

```python
# 3.0
tool.on_start(lambda tool: print("started"))
tool.on_done(lambda tool: print("done"))
await tool.trigger()
```

In 2.x, a tool could call `self.on_done()` to refresh its diagram, because the `Diagram`
assigned its `refresh()` method to `on_done`. A tool that did its work outside `run()`
used this call. In 3.0, the call raises `TypeError`, because `on_done` registers a
callback. This change affects subclasses of `Tool` that call `self.on_done()`.

```python
# 2.x: a tool that did its work outside run() and refreshed the diagram
from ipyelk import from_element
from ipyelk.elements import Node
from ipyelk.pipes import flows as F


class Hide(Tool):
    def hide(self):
        self.tee.inlet.flow = self.reports  # change the elements here
        self.on_done()


hide = Hide(reports=(F.Node.hidden,))
from_element(Node(id="root")).register_tool(hide)
hide.hide()
```

The 2.x code raises this error on 3.0:

```text
TypeError: Tool.on_done() missing 1 required positional argument: 'callback'
```

In 3.0, call `self.trigger()` instead. After a successful run, the tool records its
change reports and calls its `on_done` callbacks, which include `Diagram.refresh()`. If
the work stays outside `run()`, give the tool a `run()` that does nothing.

```python
# 3.0: trigger() records the change reports and refreshes the diagram
from ipyelk import from_element
from ipyelk.elements import Node
from ipyelk.pipes import flows as F


class Hide(Tool):
    def hide(self):
        # change the elements here
        return self.trigger()

    async def run(self):
        pass  # the work is in hide()


hide = Hide(reports=(F.Node.hidden,))
from_element(Node(id="root")).register_tool(hide)
await hide.hide()
```

(migration-callback-argument)=

#### Callbacks receive the object that calls them

Every callback receives the object that calls it. `Toolbar` calls `on_close(toolbar)`
when you click its close button. In 2.x, `Toolbar` called `on_close()` with no argument.
`Diagram.refresh(sender=None)` ignores its argument, so you can register it as an
`on_done` callback. In 2.x, the argument was `change`.

This change affects code that sets `Toolbar.on_close` to a function with no parameters.
The change is in [#157].

```python
# both versions
from ipyelk.tools import Toolbar

toolbar = Toolbar()
```

```python
# 2.x
toolbar.on_close = lambda: print("closed")
toolbar.close_btn.click()
```

On 3.0, the callback does not run. In a notebook, the click shows this error:

```text
TypeError: <lambda>() takes 0 positional arguments but 1 was given
```

```python
# 3.0
toolbar.on_close = lambda toolbar: print("closed")
toolbar.close_btn.click()
```

#### `SetTool` observes `active` with a private method

`SetTool` moves its CSS classes when `active` changes. In 2.x, the observer that did
this was the public method `SetTool.handler`. In 3.0, the observer is the private method
`_update_active`. It is not a way to request a run.

This change affects code that calls `SetTool.handler` directly. The change is in [#157].

```python
# both versions
from ipyelk.elements import Node
from ipyelk.tools import SetTool

node = Node(id="n1")
set_tool = SetTool()
```

```python
# 2.x
set_tool.handler(None)
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.handler was removed in ipyelk 3.0. It was three different things (the execution method, ToolButton's click callback trait, and SetTool's trait observer). Call tool.trigger() to request execution; pass ToolButton(on_click=callback) for a button callback (called as callback(tool)).
```

```python
# 3.0: set active, and the observer moves the classes
set_tool.active = (node,)
print(node.properties.cssClasses)
```

(migration-disabled)=

### Disable a tool with `disabled`

`Tool.disabled` replaces the `disable` trait. In 2.x, no code read `disable`, so it
disabled nothing. In 3.0, `disabled` stops the tool:

- `trigger()` raises `RuntimeError`. Nothing is scheduled, and no callback fires.
- A click on a `ToolButton` does not run its callback. In a notebook, the click shows
  the `RuntimeError`.
- Every control under `tool.ui` that has a `disabled` trait is disabled. Boxes and
  progress bars have no `disabled` trait.

This change affects code that sets `tool.disable`. The change is in [#157].

```python
# both versions: a tool that prints when it runs
from ipyelk.tools import Tool


class Hello(Tool):
    async def run(self):
        print("hello")


tool = Hello()
```

```python
# 2.x
tool.disable = True
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Tool.disable was removed in ipyelk 3.0: nothing read it, so it never disabled anything. Use tool.disabled (the ipywidgets name), which rejects trigger() and clicks and disables the controls under tool.ui.
```

```python
# 3.0
tool.disabled = True
try:
    tool.trigger()
except RuntimeError as error:
    print(error)
```

(migration-unbound)=

### Bind a tool after you make it

A dependency of a tool is a trait that the tool must have before it can run. A tool that
has a dependency with the value `None` is an unbound tool. In 3.0, `ipyelk` supports
unbound tools. You can make a tool first and bind it later, with
`Diagram.register_tool()` or an assignment.

These dependencies are `None` until you bind them:

- `PipelineProgressBar.pipe`
- `ToggleCollapsedTool.selection`
- `SetTool.selection`

In 2.x, a read of one of these traits before you set it raised `TraitError`. In 3.0, an
unbound tool disables its controls. `Tool.missing_dependencies()` names the dependencies
that are `None`, and `trigger()` raises `RuntimeError` that names them.

This change affects code that expects `TraitError` when it reads one of these traits.
The change is in [#157].

```python
# 2.x
from ipyelk.tools import ToggleCollapsedTool

print(ToggleCollapsedTool().selection)
```

In 2.x, the code raised `TraitError`. On 3.0, it prints:

```text
None
```

```python
# 3.0
from ipyelk import Diagram
from ipyelk.tools import ToggleCollapsedTool

tool = ToggleCollapsedTool()
print(tool.missing_dependencies())
try:
    tool.trigger()
except RuntimeError as error:
    print(error)
Diagram().register_tool(tool)
print(tool.missing_dependencies())
```

(migration-record-reports)=

### Tools add their change reports to the pending flow

A pipe is an `ipyelk.pipes.Pipe`, one stage in the processing of a diagram. A tool sends
its changes to the pipe in `tool.tee`. A change report is a string in `Tool.reports`
that names a kind of change, for example `"node.properties.hidden"`. The pending flow is
the tuple `pipe.inlet.flow`. It holds the change reports that the next call to
`Diagram.refresh()` processes.

In 2.x, a tool replaced the pending flow with its own change reports. Thus, two tools
that ran in the same turn of the event loop lost the change reports of the first tool.
In 3.0, a tool adds its change reports to the pending flow when its run finishes. The
new method `Tool.record_reports()` keeps the order and drops duplicates.
`ToggleCollapsedTool.run()` no longer sets the pending flow.

This change affects subclasses of `Tool` that set `self.tee.inlet.flow`. The 2.x code
does not raise an error. If it replaces the pending flow, it still drops the change
reports of other tools. The change is in [#157].

```python
# both versions: a pipe with a change report from another tool
from ipyelk.pipes import Pipe
from ipyelk.pipes import flows as F
from ipyelk.tools import Tool

pipe = Pipe()
pipe.inlet.flow = (F.Layout,)
```

```python
# 2.x: the tool replaced the pending flow
class Hide(Tool):
    async def run(self):
        self.tee.inlet.flow = self.reports


await Hide(tee=pipe, reports=(F.Node.hidden,)).trigger()
print(pipe.inlet.flow)
```

On 3.0, the 2.x code prints a pending flow without the `layout` change report of the
other tool:

```text
('node.properties.hidden',)
```

```python
# 3.0: let the base class record the change reports when the run finishes
class Hide(Tool):
    async def run(self):
        pass  # change the elements here


await Hide(tee=pipe, reports=(F.Node.hidden,)).trigger()
print(pipe.inlet.flow)
```

If a tool must record its change reports before its run finishes, call
`self.record_reports()`.

### Resolve a selection that has unknown ids

`Selection.elements()` gets the elements of the selected ids. By default, it raises
`NotFoundError` for an id that is not in the index of the diagram. The new keyword
`elements(strict=False)` skips unknown ids. The new method `missing_ids()` returns them.
Both keep the order of `ids`.

`ipyelk` does not remove unknown ids from `Selection.ids`. Thus, you can select ids
before the first layout. `Selection.get_index()` now makes the index when the index has
no elements. In 2.x, `get_index()` never made it.

This change affects code that catches `NotFoundError` to skip unknown ids. The change is
in [#157].

```python
# both versions: a diagram with a selection of one known id and one unknown id
from ipyelk import from_element
from ipyelk.elements import Node

diagram = from_element(Node(id="root", children=[Node(id="n1")]))
selection = diagram.view.selection
selection.ids = ("n1", "missing")
```

```python
# 2.x
list(selection.elements())
```

The 2.x code still raises `NotFoundError` on 3.0, and the message names the unknown id:

```text
NotFoundError: Element with id:missing not in index
```

```python
# 3.0
print([element.id for element in selection.elements(strict=False)])
print(selection.missing_ids())
```

(migration-selection-ids)=

### Compare `Selection.ids` to a tuple

`Selection.ids` is a tuple, in 2.x and in 3.0. 3.0 documents it as a tuple. A comparison
of `ids` to a list is always `False`. The `01_Linking` example now compares `ids` to a
tuple.

This change affects code that compares `Selection.ids` to a list. The change is in
[#157].

```python
# both versions
from ipyelk.tools import Selection

selection = Selection(ids=("n1",))
```

```python
# 2.x
print(selection.ids == ["n1"])
```

The 2.x code prints:

```text
False
```

```python
# 3.0
print(selection.ids == ("n1",))
```

### Type-check `Toolbar.order()` as tool widgets

`Toolbar.order()` returns a `dict[int, list[DOMWidget]]`, and `Toolbar.tool_order()`
returns a `list[DOMWidget]`. These are the `ui` widgets of the tools, not the tools. The
methods returned these widgets in 2.x too, but their 2.x type annotations named `Tool`.
A tool without a `ui` is not in the result.

This change affects only code that a type checker checks against the 2.x annotations.
The code runs as before. The change is in [#157].

(migration-hovered-id)=

### Read the hovered element from `Hover.hovered_id`

`Hover.hovered_id` replaces `Hover.ids`. Its type is `str | None`, and its default is
`None`. In spite of its name, `Hover.ids` held only one id, as a string. The value has
the same type, but the trait has a new name and can be `None`. `ipyelk` has no alias for
`ids`. `Selection.ids` does not change and is still a tuple.

This change affects code that reads or observes `ids` on a `Hover` tool, for example
`diagram.view.hover`. The change is in [#157].

```python
# both versions
from ipyelk.tools import Hover

hover = Hover()
```

```python
# 2.x
print(hover.ids)
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Hover.ids was removed in ipyelk 3.0: despite the plural name it only ever held one id (a str), and it never cleared on pointer leave. Use hover.hovered_id (str | None; None once the pointer leaves). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
print(hover.hovered_id)  # the id under the pointer, or None
hover.hovered_id = "n1"  # highlight an element from the kernel
hover.hovered_id = None  # remove the highlight
```

(migration-hover-leave)=

### Expect `None` when the pointer leaves an element

When the pointer leaves the elements of the diagram, `hovered_id` becomes `None`. In
2.x, `ids` kept the last hovered id.

This change affects observers of the hovered id that expect a string. The 2.x code does
not raise an error when you rename `ids` to `hovered_id`. But an observer that uses
string methods fails when the pointer leaves. The change is in [#157].

```python
# both versions
from ipyelk.tools import Hover

hover = Hover()
```

```python
# 2.x, with ids renamed to hovered_id: the observer expects a string
hover.observe(lambda change: print(change.new.upper()), "hovered_id")
hover.hovered_id = "n1"
hover.hovered_id = None  # what the browser writes when the pointer leaves
```

The 2.x code prints `N1` and then raises this error on 3.0:

```text
AttributeError: 'NoneType' object has no attribute 'upper'
```

```python
# 3.0
def show(change):
    print("nothing" if change.new is None else change.new.upper())


hover.observe(show, "hovered_id")
hover.hovered_id = "n1"
hover.hovered_id = None
```

(migration-painter)=

### Paint elements with `Viewer.painter`

A viewer is the `Viewer` widget of a diagram, `diagram.view`. A view is one display of a
viewer in the browser. `Viewer.painter` is an `ipyelk.tools.Painter`. In 3.0, it adds
CSS classes to the elements in each view of the viewer. The painted classes are
temporary. They do not change `properties.cssClasses` or the JSON that `ipyelk` sends to
the Eclipse Layout Kernel (ELK), the library that lays out the diagram.

- `paint(ids, *css_classes)` adds classes to the elements. `ids` is one id, one element,
  or a sequence of ids and elements.
- `unpaint(ids, *css_classes)` removes classes. With no classes, it removes the ids.
- `clear()` removes every class that the painter added. It never removes a class that is
  in `properties.cssClasses`.
- `styles` is the synced `dict[str, tuple[str, ...]]` of ids to painted classes.
- `painted_ids`, `elements(strict=True)` and `missing_ids()` work like the methods of
  `Selection`.

The 2.x placeholders `cssClasses`, `marks` and `name` are removed. They painted nothing.

This change affects code that sets `cssClasses`, `marks` or `name` on a `Painter`. The
change is in [#157].

```python
# 2.x
from ipyelk.tools import Painter

Painter(marks=["n1"])
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Painter.marks was removed in ipyelk 3.0: it was an unfinished placeholder that painted nothing. Use painter.paint(ids_or_elements, *css_classes); painter.painted_ids lists what is painted. No alias: this error is raised throughout 3.x.
```

```python
# 3.0
from ipyelk import Diagram

painter = Diagram().view.painter
painter.paint(["n1", "n2"], "highlight")
painter.unpaint("n1", "highlight")
print(painter.styles)
painter.clear()
```

## Diagrams and viewers

These sections describe the `Diagram` and its viewer, `diagram.view`. A viewer can have
more than one view.

### Override `fit()` and `center()` with the full signatures

`Viewer.fit()` and `Viewer.center()` have the same signatures as the methods of
`SprottyViewer`. Sprotty is the library that draws the diagram in the browser.

- `fit(model_ids=None, animate=None, max_zoom=None, padding=None)`
- `center(model_ids=None, animate=None, retain_zoom=None)`

`model_ids` is one id or a sequence of ids. A `str` is one id, never a sequence of
characters. A `list[str]` still works. On the generic `Viewer`, the two methods do
nothing. In 2.x, the Fit and Center buttons of the generic `Viewer` raised `TypeError`.

This change affects subclasses of `Viewer` that override `fit()` or `center()` with the
2.x signature, which had no parameters. The change is in [#157].

```python
# 2.x
from ipyelk.diagram import Viewer


class MyViewer(Viewer):
    def fit(self):
        print("fit")


MyViewer().fit("n1")
```

The 2.x code raises this error on 3.0:

```text
TypeError: MyViewer.fit() takes 1 positional argument but 2 were given
```

```python
# 3.0
from ipyelk.diagram import Viewer


class MyViewer(Viewer):
    def fit(self, model_ids=None, animate=None, max_zoom=None, padding=None):
        print("fit", model_ids)


view = MyViewer()
view.fit("n1")
view.fit_tool.ui.click()
```

### Add a `ControlOverlay` before you use it

`Viewer.control_overlay` is `None` by default. In 2.x, every viewer had a
`ControlOverlay`. To show widgets over the diagram, assign a `ControlOverlay` first. The
browser shows no overlay when `control_overlay` is `None` or has no `children`. In 2.x,
every selection made an empty overlay node in the page. The browser draws the overlay
again when its `children` change.

This change affects code that sets `view.control_overlay.children` without an assignment
of `control_overlay` first. The change is in [#157].

```python
# both versions
import ipywidgets as W
from ipyelk import Diagram

view = Diagram().view
button = W.Button(description="Hello")
```

```python
# 2.x
view.control_overlay.children = [button]
```

The 2.x code raises this error on 3.0:

```text
AttributeError: 'NoneType' object has no attribute 'children'
```

```python
# 3.0
from ipyelk.tools import ControlOverlay

view.control_overlay = ControlOverlay()
view.control_overlay.children = [button]
view.control_overlay.children = []  # shows nothing
```

(migration-viewport)=

### Read the camera from `Viewer.viewport`

The camera of a view is the part of the diagram that the view shows. `Viewer.viewport`
is an `ipyelk.tools.Viewport`. When the camera of a view moves, the browser writes the
new camera to `Viewer.viewport`. This write is a camera report. Thus, `Viewport` holds
the camera of the view that sent the last camera report. `Viewport` replaces the `Zoom`
and `Pan` tools and the `Viewer.viewed` trait. No code wrote to these 2.x names.

`Viewport` has five traits, and the browser writes them together in one camera report:

- `view_id` is the id of the view that sent the camera report.
- `origin` is the position of the top-left corner of the view, in diagram coordinates.
- `zoom` is the number of CSS pixels for each diagram unit.
- `canvas_size` is the size of the view, in CSS pixels.
- `viewed_ids` is the ids of the elements that the view shows, in diagram order. Edges
  are not in `viewed_ids`.

Each trait is `None` until the first camera report. When an observer of one trait runs,
the other traits already hold the values of the same camera report. Kernel code cannot
set the traits. Each view keeps its own camera, and each camera report names its view.

This change affects code that reads `view.zoom`, `view.pan` or `view.viewed`. The change
is in [#157].

```python
# both versions
from ipyelk import Diagram

view = Diagram().view
```

```python
# 2.x
print(view.zoom.zoom)
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Viewer.zoom was removed in ipyelk 3.0: the Zoom tool was a placeholder that nothing ever wrote. Read viewer.viewport.zoom (the browser's latest report, None until one arrives) and move a view with viewer.set_viewport(zoom=...). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
viewport = view.viewport
print(viewport.zoom, viewport.origin, viewport.viewed_ids)  # None before the first camera report
viewport.observe(lambda change: print(viewport.view_id), "origin")
```

### Move the camera with `set_viewport()`

`SprottyViewer.set_viewport(*, origin=None, zoom=None, animate=True, view_id=None)`
moves the camera. It is a command, not a trait. `origin=None` and `zoom=None` keep the
current values of the view. `view_id=None` moves every view of the viewer. After the
move, the browser sends a camera report to `Viewer.viewport`.

This change affects code that sets the traits of the 2.x `Zoom` or `Pan` tools to move
the camera. These traits did not move it. The change is in [#157].

```python
# both versions
from ipyelk import Diagram

view = Diagram().view
```

```python
# 2.x
view.pan.origin = (0, 0)
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: Viewer.pan was removed in ipyelk 3.0: the Pan tool was a placeholder that nothing ever wrote. Read viewer.viewport.origin and viewer.viewport.canvas_size (the browser's latest report, None until one arrives) and move a view with viewer.set_viewport(origin=(x, y)). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
view.set_viewport(origin=(0, 0), zoom=1.5)  # every view, animated
view.set_viewport(zoom=2, animate=False, view_id=view.viewport.view_id)
```

### Make a new diagram or tool after you close one

A closed `Diagram`, `Pipe` or tool raises `ipyelk.exceptions.ClosedError` when you use
it. A `Pipeline` is a pipe that runs a list of other pipes, its stages. A closed widget
has no connection to the browser, so a call to it cannot reach the browser. In 2.x, the
call did nothing, and no error showed.

- On a closed `Diagram`, `refresh()`, `register_tool()` and an assignment to `source`,
  `pipe`, `view`, `tools`, `toolbar`, `symbols` or `style` raise `ClosedError`.
- On a closed `Pipe`, `schedule_run()` raises `ClosedError`. On a closed `Pipeline`,
  `run()` and an assignment to `pipes` raise it too.
- A refused `pipes` assignment keeps the stages. In 2.x, it removed them.
- A diagram whose pipe is closed raises `ClosedError` on `refresh()`.
- When a pipeline closes while it processes a diagram, it stops before the next stage.
  The task that `refresh()` returned is then cancelled, so `await diagram.refresh()`
  raises `asyncio.CancelledError`.
- When a run fails just before its pipe closes, the task keeps the exception. The closed
  pipe does not call its `on_error` callback. It logs a warning that names the
  exception.
- A diagram closes its tools when it closes. On a closed tool, `trigger()` raises
  `ClosedError`. In a notebook, a click on a closed `ToolButton` shows the error.
- A second `close()` still does nothing.

`ClosedError` is a subclass of `traitlets.TraitError` and of `RuntimeError`. Thus, an
`except TraitError` clause or an `except RuntimeError` clause catches it. The new
properties `Diagram.closed` and `Pipe.closed` are `True` after a call to `close()`.

This change affects code that uses a diagram, a pipe or a tool after `close()`. The
change is in [#202].

```python
# both versions
from ipyelk import Diagram, from_element
from ipyelk.elements import Node

diagram = from_element(Node(id="root"))
diagram.close()
```

```python
# 2.x
diagram.refresh()
```

The 2.x code raises this error on 3.0:

```text
ClosedError: Diagram is closed and cannot refresh; build a new Diagram
```

```python
# 3.0: make a new diagram from the source, which stays open
if diagram.closed:
    diagram = Diagram(source=diagram.source)
diagram.refresh()
```

The `ClosedError` of a closed tool names the class of the tool, as the `ClosedError` of
a closed diagram does. The new property `Tool.closed` is `True` after a call to
`close()`. The change is in [#226].

```python
# 2.x
diagram.view.fit_tool.ui.click()
```

In a notebook, the click shows this error on 3.0:

```text
ClosedError: FitTool is closed and cannot run; build a new FitTool
```

```python
# 3.0: make a new diagram, which makes new tools
fit = diagram.view.fit_tool
if fit.closed:
    diagram = Diagram(source=diagram.source)
    fit = diagram.view.fit_tool
fit.ui.click()
```

(migration-value-sync)=

### Call `sync_value()` for browser code that reads a mark

A `MarkElementWidget` syncs its `value` with the browser only when a browser stage
reads or writes the `value`. These marks sync their `value`:

- the inlet of a `SyncedInletPipe`
- the outlet of a `SyncedOutletPipe`, such as `ElkJS` and `BrowserTextSizer`
- the `source` of a viewer

These objects call `MarkElementWidget.sync_value()` when they take the mark. Every other
mark keeps its `value` in the kernel, for example `Diagram.source`. A browser write to
a `value` that does not sync has no effect. The `flow` and `index` of a mark never sync,
because no browser code reads them.

This change affects browser code that reads the `value` of another mark. Call
`sync_value()` on that mark first. The change is in [#161].

```python
# both versions
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget

mark = MarkElementWidget(value=Node(id="root"))
```

```python
# 2.x: this printed True
print("value" in mark.get_state())
```

```python
# 3.0: sync the value of a mark that your browser code reads
mark.sync_value()
print("value" in mark.get_state())
```

(migration-markindex-widget)=

### Use a `MarkIndex` as a kernel object, not as a widget

In 3.0, a `MarkIndex` is a plain `traitlets.HasTraits`, not a widget. The `MarkIndex`
lives only in the kernel, so it opens no comm, and `MarkElementWidget.index` is never
sent to the browser. A `MarkElementWidget` is a `Widget`, not a `DOMWidget`, because no
view displays it. Thus, a `MarkElementWidget` has no `layout`, and its browser model is
a `WidgetModel`. One `Diagram()` opens 52 widgets in 3.0. In 2.x, it opened 76 widgets.

Every stage of a pipe shares the `MarkIndex` of the source, as in 2.x. The pipe builds
the `MarkIndex` when a stage first reads it. When you replace the tree of the source,
set `source.index.elements = None`. The next run then builds the index again for the new
tree. This works as in 2.x.

This change affects these uses:

- code that uses a `MarkIndex` as a widget: `.comm`, `close()`, `display()` or
  `widget_serialization`
- browser code that reads `mark.get('index')`
- code that reads `layout` of a `MarkElementWidget`

`MarkIndex.comm`, `MarkIndex.close` and `MarkElementWidget.layout` raise
`DeprecatedAPIError` throughout 3.x. The change is in [#237].

```python
# both versions
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget

mark = MarkElementWidget(value=Node(id="root"))
```

```python
# 2.x: the index was a widget, so code closed it with the mark
mark.index.close()
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: MarkIndex is not a widget in ipyelk 3.0: it lives only in the kernel, so it has no comm and nothing to close. Its elements and document work as in 2.x. No alias: this error is raised throughout 3.x.
```

```python
# 2.x: a mark had a layout, which no view used
mark.layout
```

The 2.x code raises this error on 3.0:

```text
DeprecatedAPIError: MarkElementWidget is not a DOMWidget in ipyelk 3.0: no view displays it, so it has no layout. No alias: this error is raised throughout 3.x.
```

```python
# 3.0: drop the elements to rebuild the index, and close the mark only
mark.value = Node(id="new-root")
mark.index.elements = None
mark.build_index()
print(mark.index.document["new-root"] is mark.value)
mark.close()
```

## Elements and layout options

An option id is the full id of a layout option of the Eclipse Layout Kernel (ELK), for
example `org.eclipse.elk.spacing.edgeEdge`. An option class is a class in
`ipyelk.elements.layout_options` that writes one option id, for example `EdgeSpacing`.
The `layoutOptions` dictionary of an element maps option ids to values.

(migration-option-ids)=

### Option classes use the option ids that ELK knows

Some 2.x option classes wrote option ids that ELK does not know. ELK ignored these
options and showed no error. In 3.0, these option classes write the correct option ids.
Thus, these options now change the layout. A unit test checks each option class against
the options of the bundled `elkjs`, the JavaScript version of ELK.

| Option class           | 2.x option id                                  | 3.0 option id                                           |
| ---------------------- | ---------------------------------------------- | ------------------------------------------------------- |
| `EdgeSpacing`          | `org.eclipse.elk.edge.edgeEdge`                | `org.eclipse.elk.spacing.edgeEdge`                      |
| `EdgeNodeSpacing`      | `org.eclipse.elk.edge.edgeNode`                | `org.eclipse.elk.spacing.edgeNode`                      |
| `EdgeLabelSpacing`     | `org.eclipse.elk.edge.edgeLabel`               | `org.eclipse.elk.spacing.edgeLabel`                     |
| `EdgeEdgeLayerSpacing` | `org.eclipse.elk.edge.edgeEdgeBetweenLayers`   | `org.eclipse.elk.layered.spacing.edgeEdgeBetweenLayers` |
| `EdgeNodeLayerSpacing` | `org.eclipse.elk.edge.edgeNodeBetweenLayers`   | `org.eclipse.elk.layered.spacing.edgeNodeBetweenLayers` |
| `LayoutPartitioning`   | `org.eclipse.elk.partitioning.active`          | `org.eclipse.elk.partitioning.activate`                 |
| `ConsiderModelOrder`   | `org.eclipse.elk.layered.considerModelOrder`   | `org.eclipse.elk.layered.considerModelOrder.strategy`   |
| `ContentAlignment`     | the same id, with a tab character at the start | `org.eclipse.elk.contentAlignment`                      |

Other option classes change too:

- `ConsiderModelOrder` applies only to parents and has the new value `PREFER_NODES`.
- `PortAlignmentEast`, `PortAlignmentWest`, `PortAlignmentNorth` and
  `PortAlignmentSouth` are subclasses of `PortAlignment`. Thus, they have a value and a
  control, and they apply to nodes.
- `Record` nodes set `EdgeNodeSpacing(spacing=0)`, which now has an effect.

This change affects code that uses these option classes, and code that writes the 2.x
option ids in `layoutOptions`. The 2.x code does not raise an error. But the layout of a
diagram that uses these option classes can change. ELK still ignores a 2.x option id in
`layoutOptions`. The change is in [#192].

```python
# 2.x
from ipyelk.elements import layout_options as opt

print(opt.EdgeSpacing().identifier)
```

On 3.0, the option class writes a different option id:

```text
org.eclipse.elk.spacing.edgeEdge
```

The new function `ipyelk.schema.unknown_layout_options(keys)` finds the keys that ELK
does not know. Use it to find 2.x option ids in your `layoutOptions`.

```python
# 3.0
from ipyelk.elements import Node
from ipyelk.schema import unknown_layout_options

node = Node(
    layoutOptions={
        "org.eclipse.elk.edge.edgeEdge": "5",  # the 2.x id
        "org.eclipse.elk.spacing.edgeEdge": "5",
    }
)
print(unknown_layout_options(node.layoutOptions))
```

(migration-label-port)=

### Set the label-port spacing in each direction

`LabelPortHorizontalSpacing` and `LabelPortVerticalSpacing` replace `LabelPortSpacing`.
ELK has no `spacing.labelPort` option, so ELK ignored `LabelPortSpacing`. In 3.0,
`LabelPortSpacing` sets the horizontal spacing and shows a `DeprecationWarning`.

This change affects code that uses `LabelPortSpacing`. The change is in [#192].

```python
# 2.x
from ipyelk.elements.layout_options.port_options import LabelPortSpacing

LabelPortSpacing(spacing=3)
```

The 2.x code shows this warning on 3.0:

```text
DeprecationWarning: LabelPortSpacing is deprecated: ELK has no `spacing.labelPort` option. Use LabelPortHorizontalSpacing or LabelPortVerticalSpacing.
```

```python
# 3.0
from ipyelk.elements.layout_options.port_options import (
    LabelPortHorizontalSpacing,
    LabelPortVerticalSpacing,
)

LabelPortHorizontalSpacing(spacing=3)
LabelPortVerticalSpacing(spacing=3)
```

(migration-draw2d)=

### Select a layout algorithm other than Draw2D

The choices of `LayoutAlgorithm` no longer include Draw2D
(`org.eclipse.elk.conn.gmf.layouter.Draw2D`). `elkjs` does not have this algorithm, so a
layout that used it failed. An import of `Draw2DLayout` from
`ipyelk.elements.layout_options` or from `ipyelk.elements.layout_options.layout` raises
`DeprecatedImportError` in every 3.x release.

This change affects code that imports `Draw2DLayout` or selects the Draw2D algorithm.
The change is in [#192].

```python
# 2.x
from ipyelk.elements.layout_options import Draw2DLayout
```

The 2.x code raises this error on 3.0:

```text
DeprecatedImportError: ipyelk.elements.layout_options.layout.Draw2DLayout was removed in ipyelk 3.0: elkjs has no Draw2D algorithm (org.eclipse.elk.conn.gmf.layouter.Draw2D), so a layout that selected it failed. Select another Algorithm, for example ELKLayered, ELKBox, ELKRadial or ELKRectanglePacking from ipyelk.elements.layout_options.layout: LayoutAlgorithm(value=ELKLayered.identifier). No alias: this error is raised throughout 3.x.
```

An import from the module `ipyelk.elements.layout_options.layout` fails too:

```python
# 2.x
from ipyelk.elements.layout_options.layout import Draw2DLayout
```

The 2.x code raises the same error on 3.0. The message starts with this text:

```text
DeprecatedImportError: ipyelk.elements.layout_options.layout.Draw2DLayout was removed in ipyelk 3.0
```

```python
# 3.0
from ipyelk.elements.layout_options.layout import ELKLayered, LayoutAlgorithm

LayoutAlgorithm(value=ELKLayered.identifier)
```

(migration-layout-options)=

### Give `layoutOptions` string keys and values

The type of `layoutOptions` on elements is `LayoutOptions`, from `ipyelk.elements`. It
is `dict[str, str]`, as in the ELK JSON schema. When `ipyelk` validates an element, it
changes the values:

- A `bool` becomes `"true"` or `"false"`. A NumPy boolean, for example `np.bool_(True)`,
  does too.
- An integer becomes a string: `20` becomes `"20"`. A NumPy integer, for example
  `np.int64(20)`, does too.
- A `float` that has no fractional part and a magnitude less than `2**53` loses its
  fraction: `2.0` becomes `"2"`. ELK ignores an integer option with the value `"2.0"`.
- Another `float` becomes its `repr()`: `2.5` becomes `"2.5"`, and `1e16` becomes
  `"1e+16"`.
- Another number, for example `np.float64(12.5)`, a `Decimal` or a `Fraction`, becomes a
  plain `float` first. Thus, `np.float64(12.5)` becomes `"12.5"`.

Validation raises `ValidationError` for `nan`, an infinity, `None`, a value of another
type, or a key that is not a string. 2.x accepted these values. When `ipyelk` serializes
an element for ELK, it changes a `bool` or a number to a string too. Thus, a value that
you set in place, for example `node.layoutOptions[key] = 20`, goes to ELK as `"20"`. A
`None` that you set in place makes the serialization raise a `ValueError` that names the
key. With `exclude_none=True`, the serialization removes that key instead, and ELK uses
the default of the option. `OptionsWidget.value` accepts only string keys and values.

This change affects code that puts `None`, `nan` or an object other than a string, a
number or a `bool` in `layoutOptions`. Code that puts `2.0` there also changes: ELK now
applies the option. The change is in [#192].

```python
# 2.x
from ipyelk.elements import Node

Node(layoutOptions={"org.eclipse.elk.direction": None})
```

The 2.x code raises this error on 3.0:

```text
ValidationError: 1 validation error for Node
layoutOptions.`org.eclipse.elk.direction`
  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
```

```python
# 2.x: a None that you set in place
from ipyelk.elements import Node

node = Node(layoutOptions={})
node.layoutOptions["org.eclipse.elk.direction"] = None
node.model_dump()
```

On 3.0, the serialization raises `PydanticSerializationError`, a subclass of
`ValueError`, with this message:

```text
PydanticSerializationError: Error calling function `serialize_layout_options`: ValueError: layoutOptions['org.eclipse.elk.direction'] is None: ELK cannot read it. Delete the key to unset the option.
```

```python
# 3.0: leave out the key, and use a number or a string
from ipyelk.elements import Node

node = Node(layoutOptions={"org.eclipse.elk.partitioning.partition": 2.0})
print(node.layoutOptions)
```

(migration-unknown-keys)=

### An unknown key on an element raises

An unknown key is a keyword argument or a dictionary key that a class has no field for.
In 3.0, these classes raise `ValidationError` for an unknown key when you make an
object:

- `Node`, `Port`, `Label`, `Edge`, `EdgeSection` and their subclasses
- the properties classes, for example `NodeProperties`
- the shape classes, for example `Rect`

In 2.x, these classes ignored an unknown key. Thus a typo such as `Node(hieght=5)` did
nothing, and the node kept no height. A shape also rejects a field of another shape
class. For example, `Rect(start="arrow")` raises, because `start` is a field of
`EdgeShape`. A `Point` now ignores an unknown key. 2.x raised `TypeError` for one.

Assignment does not change. In both versions, `node.hieght = 5` raises `ValidationError`
for an element or its properties, and a shape raises `ValueError`. `layoutOptions`
accepts any option id, as in 2.x.

ELK JSON can have keys that the models do not have, for example the `$H` key that elkjs
adds. Thus `convert_elkjson`, `from_elkjson`, the value that comes back from the
frontend and the `networkx` loader ignore those keys. To load a dictionary of your own
in the same way, use `ipyelk.elements.from_wire(Node, data)`. In 3.0,
`Node.model_validate(data)` raises for an unknown key.

This change affects code that passes a misspelled key or a key of another class. It also
affects code that loads ELK JSON with `Node.model_validate`. The change is in [#233].

```python
# 2.x
from ipyelk.elements import Node

Node(id="a", hieght=5)
```

The 2.x code raises this error on 3.0:

```text
ValidationError: 1 validation error for Node
hieght
  Extra inputs are not permitted [type=extra_forbidden, input_value=5, input_type=int]
```

```python
# 3.0
from ipyelk.elements import Node

node = Node(id="a", height=5)
print(node.height)
```

```python
# 2.x: ELK JSON with a key that the models do not have
from ipyelk.elements import Node

Node.model_validate({"id": "root", "$H": 123})
```

The 2.x code raises this error on 3.0:

```text
ValidationError: 1 validation error for Node
$H
  Extra inputs are not permitted [type=extra_forbidden, input_value=123, input_type=int]
```

```python
# 3.0: from_wire ignores the keys that the models do not have
from ipyelk.elements import Node, from_wire

root = from_wire(Node, {"id": "root", "$H": 123})
print(root.id)
```

(migration-shape-classes)=

### JSON loads a shape as the class of its type string

The type string of a shape is its `type` field, for example `node:path`. The type string
selects the renderer in the frontend. In 3.0, ELK JSON loads each shape as the class of
its type string. ELK JSON loads through `convert_elkjson`, `from_elkjson` and the value
that comes back from the frontend after each layout. Thus a `Path`, a `Comment` or a
`Widget` keeps its class and its fields. 2.x loaded every shape as the shape class of
its element, for example `NodeShape`.

This change affects code that reads the shapes of a loaded tree. It also affects code
that loads JSON with incomplete shapes, and code that defines shape classes. The change
is in [#233].

#### A shape must have the fields of its class

The class of the type string validates the shape. If the JSON does not have a field that
the class requires, loading raises `ValidationError`. 2.x loaded the shape as a
`NodeShape`. For example, a `node:path` shape without `use` raises.

```python
# 2.x: a node:path shape without use
from ipyelk.elements import convert_elkjson

shape = {"type": "node:path"}
convert_elkjson({"id": "root", "children": [{"id": "a", "properties": {"shape": shape}}]})
```

The 2.x code raises this error on 3.0:

```text
ValidationError: 1 validation error for Node
children.0.properties.shape.use
  Field required [type=missing, input_value={'type': 'node:path'}, input_type=dict]
```

```python
# 3.0: give each shape the fields that its class requires
from ipyelk.elements import convert_elkjson

shape = {"type": "node:path", "use": "M 0,0 L 10,10"}
root = convert_elkjson({"id": "root", "children": [{"id": "a", "properties": {"shape": shape}}]})
print(type(root.children[0].properties.shape).__name__)
```

#### A `Circle` loads as an `Ellipse`

`Circle` and `Ellipse` have the same type string, `node:round`. The JSON does not hold
`radius`, `rx` or `ry`. Thus a `node:round` shape loads as an `Ellipse` with the `width`
and `height` of the JSON. The renderer draws both shapes from the width and the height,
so the diagram does not change. `isinstance(shape, Circle)` is `False` after a load, in
both versions.

```python
# both versions: the JSON of a node with a Circle shape
from ipyelk.elements import Node, NodeProperties, convert_elkjson, shapes
from ipyelk.elements.serialization import to_json

circle = NodeProperties(shape=shapes.Circle(radius=7))
data = to_json(Node(id="root", children=[Node(id="a", properties=circle)]), None)
```

```python
# 2.x: this printed NodeShape 14.0
shape = convert_elkjson(data).children[0].properties.shape
print(type(shape).__name__, shape.width)
```

The 2.x code shows this on 3.0:

```text
Ellipse 14.0
```

```python
# 3.0: read the size from width and height
shape = convert_elkjson(data).children[0].properties.shape
print(shape.width / 2)
```

#### A widget shape needs an open widget

A `node:widget` shape loads as a `Widget` with the widget that has the `model_id` in
`use`. If no open widget has that `model_id`, the shape loads as a `NodeShape` with the
same JSON, and `ipyelk` shows a `UserWarning`. This occurs when the widget closed, or
when the JSON comes from another kernel.

```python
# 2.x: JSON with the model_id of a widget that is not open
from ipyelk.elements import convert_elkjson

shape = {"type": "node:widget", "use": "abc123"}
root = convert_elkjson({"id": "root", "children": [{"id": "a", "properties": {"shape": shape}}]})
print(type(root.children[0].properties.shape).__name__)
```

The 2.x code shows this warning on 3.0, and loads a `NodeShape` as 2.x did:

```text
UserWarning: No open widget has the model_id 'abc123' of a 'node:widget' shape. The shape loads as a NodeShape with the same JSON.
NodeShape
```

```python
# 3.0: load the JSON while its widget is open
from ipywidgets import IntSlider

from ipyelk.elements import Node, NodeProperties, convert_elkjson, shapes
from ipyelk.elements.serialization import to_json

slider = IntSlider()
properties = NodeProperties(shape=shapes.Widget(widget=slider))
data = to_json(Node(id="root", children=[Node(id="a", properties=properties)]), None)
print(convert_elkjson(data).children[0].properties.shape.widget is slider)
```

#### A second class for a type string replaces the first

If a shape class of your own sets a new type string, the class adds itself to
`BaseShape.json_classes` when Python defines it. Then JSON loads that type string as
your class. 2.x had no `json_classes`. If your class sets a type string that another
class has, your class replaces the other class. Then `ipyelk` shows a `UserWarning`. For
example, a class `Oval` with the type string `node:round` shows this warning:

```text
UserWarning: __main__.Oval replaces ipyelk.elements.shapes.Ellipse as the class that loads the shape type 'node:round' from JSON. Give it another type, or set `loads_from_json = False` on it.
```

To keep the other class, give your class another type string, or set
`loads_from_json = False` on your class. If you define the same class again, for example
when you run a notebook cell again, `ipyelk` shows no warning.

### Expect `NotFoundError` or `NotUniqueError` from `ElementIndex.root()`

A root is a node that has no parent. `ElementIndex.root()` raises
`ipyelk.exceptions.NotFoundError` when the index has no root. It raises `NotUniqueError`
when the index has more than one root, and the message names the roots. `check_ids()`,
`check_edges()` and `MarkIndex.root()` call `root()`, so they raise these errors too.

In 2.x, an index with no root failed an `assert` with the wrong message, "Multiple
roots". An index with more than one root used the first root and showed no error. Thus,
the checks did not look at the other trees.

This change affects code that catches `AssertionError` from these methods, or that
indexes more than one tree. The change is in [#206].

```python
# both versions: an index with two roots
from ipyelk.elements import ElementIndex, Node

index = ElementIndex.from_els(Node(id="a"), Node(id="b"))
```

```python
# 2.x
print(index.root().id)
```

The 2.x code raises this error on 3.0:

```text
NotUniqueError: The index has 2 roots: a, b
```

```python
# 3.0: index one tree
from ipyelk.elements import ElementIndex, Node

index = ElementIndex.from_els(Node(id="root", children=[Node(id="a"), Node(id="b")]))
print(index.root().id)
```

### Compare `ElkLabel` objects field by field

3.0 removes `ElkLabel.__eq__` and `ElkLabel.__hash__`. They served a cache of text sizes
that is gone. `ElkLabel` now compares field by field, like the other classes in
`ipyelk.elements.layout_options.model`. You cannot put an `ElkLabel` in a `set`.

This change affects code that puts `ElkLabel` objects in a `set` or uses them as `dict`
keys. The change is in [#206].

```python
# both versions
from ipyelk.elements.layout_options.model import ElkLabel

label = ElkLabel(id="l1", text="hello")
```

```python
# 2.x
print(hash(label))
```

The 2.x code raises this error on 3.0:

```text
TypeError: unhashable type: 'ElkLabel'
```

```python
# 3.0: keep labels in a list or index them by id
labels = {label.id: label}
print(label == ElkLabel(id="l1", text="hello"))
```

(migration-wrapping-horizontal)=

### Do not use `GraphWrappingStrategy.horizontal`

3.0 removes the trait `GraphWrappingStrategy.horizontal`. No code read it, so it changed
nothing. On 3.0, `GraphWrappingStrategy(horizontal=...)` ignores the keyword and shows
no error. A later read of `horizontal` raises `AttributeError`. An assignment to
`horizontal` makes a plain Python attribute and shows no error.

`traitlets` issues a `DeprecationWarning` for the ignored keyword. A notebook shows a
`DeprecationWarning` only when the code of the notebook issues it. Thus, a notebook does
not show this warning. By default, a `pytest` run shows it in its summary of warnings.

This change affects code that sets or reads `GraphWrappingStrategy.horizontal`. No other
trait replaces it. The change is in [#206].

```python
# 2.x
from ipyelk.elements.layout_options.wrapping_options import GraphWrappingStrategy

strategy = GraphWrappingStrategy(horizontal="center")
print(strategy.horizontal)
```

The 2.x code raises this error on 3.0:

```text
AttributeError: 'GraphWrappingStrategy' object has no attribute 'horizontal'
```

```python
# 3.0: leave out horizontal
from ipyelk.elements.layout_options.wrapping_options import GraphWrappingStrategy

GraphWrappingStrategy(value="OFF")
```

(migration-label-size)=

### Expect a label to have the size that you assign

In 3.0, the layout uses the `width` and the `height` that you assign to a `Label`.
Unless the `LabelShape` of a label sets both `width` and `height`, the browser measures
the text of the label. In 2.x, the measured size then replaced the size that you
assigned. In 3.0, the layout uses the measured size only for a dimension that has no
other value.

For each dimension of a label, the layout uses the first of these values:

1. the `width` or `height` that you assigned to the `Label`
2. the `width` or `height` of its `LabelShape`
3. the size that the browser measured

This change affects code that assigns a `width` or a `height` to a `Label`. It also
affects code that sets only one of the two on a `LabelShape`. The 2.x code does not
raise an error. But the layout of the label can change. The change is in [#223].

```python
# 2.x
from ipyelk.elements import Label, LabelProperties
from ipyelk.elements.shapes import LabelShape

label = Label(text="A long label", width=40)
other = Label(
    text="A long label", properties=LabelProperties(shape=LabelShape(width=40))
)
```

On 3.0, the layout makes both labels 40 pixels wide. On 2.x, both labels had the width
of their text.

```python
# 3.0: leave out the width to lay out the label at the width of its text
from ipyelk.elements import Label

label = Label(text="A long label")
```

In 3.0, a shape also keeps its class and its fields through a layout. In 2.x, the shape
came back from the browser as its base class, for example a `Circle` as a `NodeShape`.
The element also kept its laid-out size, so a later change to the size of its shape had
no effect. In 3.0, a change to the size of a shape changes the size of the element at
the next layout. 2.x code that assigns `None` to `width` and `height` after it changes
the shape still works. The {doc}`reference/shapes` page tells you how to request that
layout.

(migration-document)=

### Find elements by id with a `Document`

A `Document` (`ipyelk.elements.Document`) owns the ids of an element tree. It replaces
the `Registry` context manager, which 3.0 deprecates. `Document(root)` gives each
element without an id the id that the element serializes with. This id is the
`wire_id` of the element. Thus, the id that the browser shows is the id that the element
keeps.

A `Document` finds an element in three ways:

- `document[id]` returns the element. It raises `NotFoundError` for an unknown id.
- `document.resolve(id)` returns a `Resolved(element, via_slack)`, or `None` for an
  unknown id.
- `document.lookup(ids, strict=True)` returns the elements of `ids`. With
  `strict=False`, it skips the unknown ids. `document.missing(ids)` lists them.

No `ipyelk` code uses a `Registry` in 3.0. A `Registry` holds an element weakly, so it
does not keep the element alive. It holds a key that cannot be weakly referenced, such
as a `str`, as in 2.x.

This change affects code that makes a `Registry` or enters one with `with`. `Registry`
works through 3.x, and `ipyelk` 4.0 removes it. The change is in [#160].

```python
# 2.x
from ipyelk.elements import ElementIndex, Node, Registry

nodes = [Node(id="n1"), Node()]
with Registry():
    el_map = ElementIndex.from_els(*nodes)
node = el_map.elements["n1"]
```

The 2.x code shows this warning on 3.0:

```text
DeprecationWarning: ipyelk.elements.Registry is deprecated and will be removed in ipyelk 4.0: a Document (ipyelk.elements.Document) owns the ids of an element tree, without a context manager. Document(root) gives each element without an id the id that it serializes with, and document.resolve(id) finds the element; to reuse a fragment, copy it with Node.clone(prefix). Registry keeps working through 3.x.
```

```python
# 3.0
from ipyelk.elements import Document, Node

nodes = [Node(id="n1"), Node()]
doc = Document(*nodes)
node = doc["n1"]
print(doc.resolve("typo"), doc.missing(["n1", "typo"]))
```

(migration-markindex-context)=

### Read the ids of a pipe from `MarkIndex.document`

`MarkIndex.document` replaces `MarkIndex.context`, which 3.0 deprecates. Every stage
and tool of a pipe shares the `MarkIndex` of the pipe. Its `document` is the `Document`
of the pipe, and `MarkIndex.elements` is the id map of that document. `MarkIndex.context`
holds a `Registry` that `ipyelk` does not read.

`MarkIndex.elements` and `MarkIndex.context` are properties in 3.0, not traits.
`MarkIndex(elements=...)` and an assignment to `elements` work as in 2.x. But
`observe(callback, "elements")` never calls the callback.

This change affects code that reads or assigns `MarkIndex.context`, and code that
observes `MarkIndex.elements`. `MarkIndex.context` works through 3.x, and `ipyelk` 4.0
removes it. The change is in [#160].

```python
# both versions
from ipyelk.elements import Node
from ipyelk.pipes import MarkElementWidget

mark = MarkElementWidget(value=Node(id="root", children=[Node()]))
mark.build_index()
element = mark.value.children[0]
```

```python
# 2.x
with mark.index.context:
    el_id = element.get_id()
```

The 2.x code shows this warning on 3.0:

```text
DeprecationWarning: MarkIndex.context is deprecated and will be removed in ipyelk 4.0: MarkIndex.document (an ipyelk.elements.Document) owns the ids, and nothing in ipyelk reads the Registry. Use index.document.resolve(id).
```

```python
# 3.0: the id that the element serializes with is the id that it keeps
el_id = element.wire_id()
print(mark.index.document[el_id] is element)
```

(migration-index-without-id)=

### Index an element that has no id

`ElementIndex.from_els`, `VisIndex.from_els` and `HierarchicalIndex.from_els` index an
element without an id by its `wire_id`. In 2.x, they raised `ValueError` outside a
`Registry`. `Painter.paint(element)` stores the `wire_id` of an element that has no id.
In 2.x, it raised `ValueError`. The `id` of the element stays `None` until a `Document`
writes it.

This change affects code that expects the `ValueError`. The change is in [#160].

```python
# both versions
from ipyelk.elements import ElementIndex, Node

node = Node()
```

```python
# 2.x: this raised ValueError("Cannot index element without an id ...")
index = ElementIndex.from_els(node)
```

```python
# 3.0
index = ElementIndex.from_els(node)
print(index.elements[node.wire_id()] is node, node.id)
```

(migration-slack-id)=

### Find the hidden element of a slack port with `Document.resolve`

A slack port is the port that the projection adds to the nearest visible ancestor of a
hidden element. The edges of the hidden element connect to the slack port. In 3.0, a
slack port has its own id: the id of the hidden element plus `.slack`. If another
element uses that id, the slack port adds `.slack` again. In 2.x, the slack port had the
id of the hidden element, so two elements had one id.

The rest stays as in 2.x:

- `Selection.elements()` returns the hidden element for the id of a slack port.
- `Document.resolve` returns the hidden element, with `via_slack=True`.
- `properties.key` of the slack port is the id of the hidden element.

`Painter.paint` of the id of a hidden element does not style its slack port. In 2.x, it
did, because the two elements had one id. To style the slack port, paint its id too.
`ElementIndex.update` does not add the slack ports of a browser answer to the index.

This change affects code that compares the id of a slack port with the id of a hidden
element, and code that paints a hidden element. The change is in [#160].

```python
# both versions: the node "h" is hidden inside the node "C"
from ipyelk.elements import Node, NodeProperties
from ipyelk.pipes import VisibilityPipe

root = Node(id="root")
compound = root.add_child(Node(id="C"))
hidden = compound.add_child(Node(id="h", properties=NodeProperties(hidden=True)))
root.add_edge(hidden, root.add_child(Node(id="shown")))
pipe = VisibilityPipe()
pipe.inlet.value = root
pipe.inlet.build_index()
await pipe.run()
(port,) = pipe.outlet.value.children[0].ports
```

```python
# 2.x: this printed True
print(port.id == hidden.id)
```

```python
# 3.0
from ipyelk.tools import Painter

document = pipe.inlet.index.document
found = document.resolve(port.id)
print(port.id, found.element is hidden, found.via_slack, port.properties.key)
slack_ids = [slack for slack, hidden_id in document.slack.items() if hidden_id == "h"]
Painter().paint(["h", *slack_ids], "highlight")
```

(migration-one-parent)=

### Give each element one parent

An element under a second parent raises `ValueError` when you attach it. The message
names both parents. While the second parent is made, the error is a
`pydantic.ValidationError`, which is a `ValueError` too. This applies to labels, child
nodes and ports. An element that its old parent no longer holds attaches without an
error.

In 2.x, a shared label failed later, in `ValidationPipe`, with "Nonunique Element Ids".
A shared child node or port failed an `assert` ("owned by different node"). A label
that you append to `labels` in place is not checked when you attach it.
`ValidationPipe` still reports its id. `Compartment(bullet_shape=...)` gives each line
its own bullet label. In 2.x, it shared one label, which failed validation.

To use one fragment in several places, copy it with `Node.clone(prefix)`. The copy of
an element with the id `X` has the id `"<prefix>.X"`.

This change affects code that puts one element under two parents. The change is in
[#160].

```python
# 2.x
from ipyelk.elements import Label, Node

label = Label(text="x")
a = Node(id="A", labels=[label])
b = Node(id="B", labels=[label])
```

The 2.x code raises this error on 3.0:

```text
Value error, Label without an id (text 'x') is already under Node 'A', so it cannot also be under Node 'B'. An element has one parent: detach it first, or use a copy (Node.clone(prefix) for a fragment, model_copy() for a label).
```

```python
# 3.0: give each parent its own label, and copy a fragment with clone
from ipyelk.elements import Label, Node

label = Label(text="x")
a = Node(id="A", labels=[label])
b = Node(id="B", labels=[label.model_copy()])
gate = Node(id="gate", children=[Node(id="core")])
root = Node(id="root", children=[gate.clone("g1"), gate.clone("g2")])
print([child.children[0].id for child in root.children])
```

## Imports

(migration-zoom-pan-import)=

### Do not import `Zoom` or `Pan`

An import of `ipyelk.tools.Zoom` or `ipyelk.tools.Pan` raises `DeprecatedImportError`.
{ref}`migration-viewport` tells you what to use instead. The change is in [#157].

This change affects code that imports `Zoom` or `Pan` from `ipyelk.tools`.

```python
# 2.x
from ipyelk.tools import Zoom
```

The 2.x code raises this error on 3.0:

```text
DeprecatedImportError: ipyelk.tools.Zoom was removed in ipyelk 3.0: it was a placeholder that nothing ever wrote. The browser reports the camera of the most recently reporting view as viewer.viewport (ipyelk.tools.Viewport: view_id, origin, zoom, canvas_size, viewed_ids); move a view with viewer.set_viewport(zoom=...). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
from ipyelk.tools import Viewport

print(Viewport().zoom)
```

(migration-control-module)=

### Import `ControlOverlay` from `ipyelk.tools.control_overlay`

The module `ipyelk.tools.contol_overlay` had a spelling mistake. Its new name is
`ipyelk.tools.control_overlay`. An import of the old module raises
`DeprecatedImportError` and names the new module. The old module exports no names. The
change is in [#157].

This change affects code that imports from `ipyelk.tools.contol_overlay`.

```python
# 2.x
from ipyelk.tools.contol_overlay import ControlOverlay
```

The 2.x code raises this error on 3.0:

```text
DeprecatedImportError: ipyelk.tools.contol_overlay (misspelled) was removed in ipyelk 3.0; import ControlOverlay from ipyelk.tools.control_overlay (or ipyelk.tools). No alias: this error is raised throughout 3.x.
```

```python
# 3.0
from ipyelk.tools import ControlOverlay
from ipyelk.tools.control_overlay import ControlOverlay as SameClass

print(ControlOverlay is SameClass)
```

(migration-mappings)=

### Do not import `ipyelk.pipes.mappings`

3.0 removes the module `ipyelk.pipes.mappings`, because no code used it. The module had
its own classes `Edge` and `Port`, which are not the classes of `ipyelk.elements`. It
also had the type aliases `NodeMap`, `EdgeMap` and `PortMap`. 3.0 has no replacement for
these names. An import of the module or of one of its names raises
`DeprecatedImportError`.

This change affects code that imports `ipyelk.pipes.mappings`. To make a graph, use the
classes `Node`, `Edge` and `Port` from `ipyelk.elements`. The change is in [#206].

```python
# 2.x
from ipyelk.pipes.mappings import NodeMap
```

The 2.x code raises this error on 3.0:

```text
DeprecatedImportError: ipyelk.pipes.mappings was removed in ipyelk 3.0: nothing in ipyelk used its Edge and Port dataclasses or its NodeMap, EdgeMap and PortMap aliases, and nothing replaces them. Build graphs from ipyelk.elements.Node, Edge and Port. No alias: this error is raised throughout 3.x.
```

```python
# 3.0: make the graph from the classes of ipyelk.elements
from ipyelk.elements import Node, Port

a = Node(id="a", ports=[Port(id="a.out")])
b = Node(id="b")
root = Node(id="root", children=[a, b])
root.add_edge(source=a.ports[0], target=b)
print(len(root.edges))
```

(migration-mark-factory)=

### Do not import `Mark` or `MarkFactory`

3.0 removes `ipyelk.elements.Mark`, `ipyelk.elements.MarkFactory` and the module
`ipyelk.elements.mark_factory`. They served the `networkx` transformer that `ipyelk`
2.0 removed, and no code used them after that. An import of the module or of one of the
names raises `DeprecatedImportError`.

This change affects code that imports these names. To use one fragment in several
places, copy it with `Node.clone(prefix)`. To load a `networkx` graph, use
`ipyelk.from_nx` or `ipyelk.loaders.NXLoader`. The change is in [#160].

```python
# 2.x
from ipyelk.elements import MarkFactory
```

The 2.x code raises this error on 3.0:

```text
DeprecatedImportError: ipyelk.elements.MarkFactory was removed in ipyelk 3.0: Mark and MarkFactory served the networkx transformer that ipyelk 2.0 removed (#90), and nothing used them since. To use one fragment in several places, copy it with Node.clone(prefix); to load a networkx graph, use ipyelk.from_nx or ipyelk.loaders.NXLoader. No alias: this error is raised throughout 3.x.
```

```python
# 3.0: copy a fragment with clone
from ipyelk.elements import Node

gate = Node(id="gate", children=[Node(id="core")])
print(gate.clone("g1").children[0].id)
```

### Do not import `NodeExpandTool` in TypeScript

The browser part of `ipyelk` is the npm package `@jupyrdf/jupyter-elk`. 3.0 removes its
TypeScript class `NodeExpandTool` and its `ExpandAction`. The `wheel` handler of
`NodeExpandTool` returned before it did anything, and no code sent `ExpandAction`. 3.0
also removes the empty `change:interaction` listener, because no kernel class has an
`interaction` trait.

This change affects only TypeScript code that imports `NodeExpandTool` or
`ExpandAction`. Python code does not change. The examples in this section are not run.
The change is in [#206].

```typescript
// 2.x
import { NodeExpandTool } from '@jupyrdf/jupyter-elk/lib/tools';
import { ExpandAction } from '@jupyrdf/jupyter-elk/lib/tools/expand';
```

On 3.0, `lib/tools` does not export `NodeExpandTool`, and the module `lib/tools/expand`
is gone. Thus, the 2.x imports fail.

```typescript
// 3.0: delete the import, because there is no replacement
```

[#157]: https://github.com/jupyrdf/ipyelk/pull/157
[#160]: https://github.com/jupyrdf/ipyelk/issues/160
[#161]: https://github.com/jupyrdf/ipyelk/issues/161
[#192]: https://github.com/jupyrdf/ipyelk/pull/192
[#202]: https://github.com/jupyrdf/ipyelk/pull/202
[#206]: https://github.com/jupyrdf/ipyelk/pull/206
[#223]: https://github.com/jupyrdf/ipyelk/pull/223
[#226]: https://github.com/jupyrdf/ipyelk/pull/226
[#233]: https://github.com/jupyrdf/ipyelk/pull/233
[#237]: https://github.com/jupyrdf/ipyelk/issues/237
