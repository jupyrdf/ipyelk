# Changelog

## `3.0.0a0` (unreleased)

> 2.1.2 and 2.1.3 were not released: their changes are in this release ([#227]).

### `ipyelk 3.0.0a0`

#### Breaking changes

- Tools no longer replace the pipe's pending flow when they run. `Tool` merges its
  `reports` into `tee.inlet.flow` (order preserved, duplicates dropped) through the new
  `Tool.record_reports()`, so two tools triggered in the same turn -- or a tool
  triggered while the initial `("new",)` flow is still unconsumed -- keep every writer's
  pending reports. `ToggleCollapsedTool.run` no longer assigns the flow itself ([#156]).
- `Viewer.fit()` / `Viewer.center()` now carry the full `SprottyViewer` signatures
  (`model_ids: str | Sequence[str] | None`, plus the animate/zoom/padding keywords) and
  are documented no-ops on the generic viewer. `model_ids` accepts one id or any
  sequence of ids (a `str` is one id, never its characters); `list[str]` still works.
  The base `Viewer`'s Fit/Center buttons no longer raise `TypeError` when clicked
  ([#156]).
- Tool invocation and lifecycle names each have one role ([#156]):
  - `Tool.trigger()` requests execution (cancels a running request, schedules `run()`,
    returns the `asyncio.Task`); `Tool.handler` is removed.
  - `ToolButton.on_click` replaces the `handler` trait; it is called as
    `on_click(tool)`.
  - `SetTool`'s `active` observer is the private `_update_active`; it is not an
    execution entry point.
  - `Tool.on_start(callback)` replaces `on_run`. It fires when the work actually starts
    (2.x `on_run` fired after a _successful_ run, despite its name).
  - `Tool.on_done(callback)` is a registration method (several listeners; the owning
    `Diagram` registers its refresh there), no longer an assignable single-slot trait.
    Callbacks receive the tool and fire **only after `run()` completes successfully and
    its change reports are recorded** -- never on failure, cancellation, or a request
    rejected by `trigger()`.
  - Reports are recorded when the work finishes (successfully or not), so partial
    changes from failed or cancelled work still reach the next refresh; a request
    superseded by a newer `trigger()` never overwrites the newer request's state.
  - `trigger()` on a tool without a `run()` (state-only tools such as `Selection`,
    callback tools such as `ToolButton`) raises `NotImplementedError` before anything is
    scheduled; nothing is faked.
  - Every callback receives the emitting object: `Toolbar.on_close` is typed `Callable`
    and called as `on_close(toolbar)`.
  - `Diagram.refresh(sender=None)` ignores its argument (it was `change`).
- `Tool.disabled` replaces the inert, synced `disable` trait (nothing ever read it). It
  is an execution guard: `trigger()` and `ToolButton` clicks are rejected with
  `RuntimeError` while the tool is disabled (nothing is scheduled, no callback fires),
  and every control under `tool.ui` that has a `disabled` trait follows it -- buttons
  and the buttons inside `SetTool`'s box, but not boxes or progress bars, which have no
  such trait ([#156]).
- Unbound tools are a supported state: `PipelineProgressBar.pipe`,
  `ToggleCollapsedTool.selection` and `SetTool.selection` are `None` until bound (they
  used to raise `TraitError` on read), so a tool can be constructed first and bound
  later (`Diagram.register_tool`, assignment, or the progress bar's first `update`).
  While a dependency listed in the tool's `_dependencies` is `None`,
  `Tool.missing_dependencies()` names it, the tool's controls are disabled, and
  `trigger()` raises `RuntimeError` naming the missing dependency ([#156]).
- `Selection.elements()` stays strict by default (an unknown id raises `NotFoundError`
  naming it) and gains explicit tolerant resolution: `elements(strict=False)` skips
  unknown ids and `missing_ids()` reports them, both in `ids` order. Requested ids are
  never filtered on assignment, so selecting before the first layout keeps working.
  `get_index()` now builds the index when the pipe's `MarkIndex` has no elements yet (it
  only checked for a missing `MarkIndex`, which always exists) ([#156]).
- `Toolbar.order()` and `Toolbar.tool_order()` are annotated as returning tool UIs
  (`dict[int, list[DOMWidget]]` / `list[DOMWidget]`), which is what they always
  returned, and document that tools without a `ui` are omitted. `Selection.ids` is
  documented as the tuple it is; the `01_Linking` example compares it to a tuple (its
  list comparison was always true), and the `12`/`13` examples drop commented-out
  references to the long-gone `toolbar.commands` ([#156]).
- `Hover.ids` is replaced by `Hover.hovered_id: str | None` (default `None`). No alias
  exists: code that reads or observes `ids` on the hover tool must switch to
  `hovered_id`. Despite its name, `ids` only ever held one id (a string, never a tuple),
  so the value shape is unchanged; only the trait name and the `None` state are new.
  `Selection.ids` is unchanged and still a tuple ([#155]).
- Leaving an element now clears the hover: `hovered_id` becomes `None` when the pointer
  leaves the diagram's elements (it previously kept the last hovered id forever).
  Observers that only expect strings must handle `None` ([#155]).
- `Viewer.control_overlay` is opt-in and defaults to `None`; assign a `ControlOverlay`
  (e.g. `view.control_overlay = ControlOverlay()`) before setting its `children`. The
  browser renders no overlay container for `None` or for an overlay without `children`
  (previously every selection rendered an empty `<id>_entropy` node), and re-renders
  when the overlay's `children` change ([#156]).
- `ipyelk.tools.contol_overlay` (sic) is renamed to `ipyelk.tools.control_overlay`
  without an alias ([#156]).
- `Viewer.viewport` (an `ipyelk.tools.Viewport`) replaces the never-written `Zoom` and
  `Pan` tools and the `Viewer.viewed` trait with real viewport synchronization ([#156]).
  The browser reports the camera of the **most recently reporting view** as one snapshot
  -- `view_id`, `origin`, `zoom`, `canvas_size`, `viewed_ids` -- so an observer of any
  field sees all five updated together. It is not a global viewport: several views of
  one diagram stay independent and each report names its view. The traits are read-only
  in the kernel (the browser is the only writer) and `None` until the first report.
  `viewed_ids` lists the model elements whose bounds touch the visible rectangle, in
  model order; edges, renderer artifacts and the slack ports/edges that stand in for
  hidden elements are never listed.
- `SprottyViewer.set_viewport(*, origin=None, zoom=None, animate=True, view_id=None)`
  moves the camera (a command, like `fit`/`center`, never a trait): `None` keeps the
  view's current origin/zoom, `view_id=None` moves every connected view ([#156]).
- `Viewer.painter` (an `ipyelk.tools.Painter`) is live: temporary, view-only styling
  ([#156]). `painter.paint(ids, *css_classes)` adds classes to the rendered elements in
  every connected view without touching `properties.cssClasses` -- a re-layout
  re-applies them, the ELK/model JSON never changes, and exported SVG shows them.
  `unpaint(ids, *css_classes)` removes classes (with none given, drops the ids),
  `clear()` removes everything the painter applied and never a class the model set,
  `painted_ids`, `elements(strict=True)` and `missing_ids()` mirror `Selection`. Targets
  are ids (a `str` is one id) or elements (stored as `get_id()`); the synced `styles`
  trait is `dict[str, tuple[str, ...]]`. The unfinished 2.x placeholders `cssClasses`,
  `marks` and `name` are removed.
- Removed names are hard errors for the whole 3.x line, not aliases or warnings:
  `Tool.handler`, `ToolButton.handler`, `Tool.on_run`, `Tool.disable`, `Hover.ids`,
  `Viewer.zoom`, `Viewer.pan`, `Viewer.viewed`, `ipyelk.tools.Zoom`, `ipyelk.tools.Pan`,
  `Painter.cssClasses`, `Painter.marks`, `Painter.name`, and assigning `Tool.on_start`
  or `Tool.on_done` raise `ipyelk.exceptions.DeprecatedAPIError` (an `AttributeError`,
  so `hasattr`, `getattr(..., default)` and introspection keep working) on read,
  assignment, and as constructor keywords, with the reason and the replacement in the
  message (mechanism: `ipyelk.exceptions.RemovedAPI` / `RegistrationMethod` /
  `check_removed`). The removed module-level _names_ raise
  `ipyelk.exceptions.DeprecatedImportError` instead, which is an `ImportError` and not
  an `AttributeError`, because `from ipyelk.tools import Zoom` would otherwise lose the
  message to a bare "cannot import name". Importing the misspelled
  `ipyelk.tools.contol_overlay` module raises it too, naming the new path; it re-exports
  nothing. Both flavors share the `ipyelk.exceptions.DeprecatedAPI` base, so one
  `except` catches either.
- Raise on a closed diagram or pipeline instead of silently accepting the call. A closed
  widget has no comm, so the call never reached the browser. `refresh()`,
  `register_tool()` and setting `source`, `pipe`, `view`, `tools`, `toolbar`, `symbols`
  or `style` on a closed `Diagram` raise `ipyelk.exceptions.ClosedError` (a `TraitError`
  and a `RuntimeError`) naming its class, as do `schedule_run()` on a closed `Pipe` and
  setting `pipes` or calling `run()` on a closed `Pipeline`. `Diagram.closed` and
  `Pipe.closed` say whether `close()` was called. A refused `pipes` set keeps the
  stages; it used to empty them. A diagram whose pipe was closed raises on `refresh()`.
  A run in flight when its pipeline closes is cancelled before the next stage or
  successful completion, even when a progress callback closes it or the cancel comes
  from another event loop during the final stage; the task `refresh()` returned then
  resolves cancelled, so `await diagram.refresh()` raises `CancelledError`. The closed
  pipe and its interrupted stages report `cancelled` instead of staying `running`,
  without firing progress callbacks or updating closed widgets. An error raised by a
  stage after its pipeline closes is treated as cancellation, including a `ClosedError`
  from another closed widget. A run that failed just before the close keeps its
  exception, and the closed pipe logs a warning naming it instead of calling `on_error`.
  A queued refresh callback does not update a closed diagram. Closed tools that
  implement `run()` reject `trigger()`, and closed `ToolButton`s reject button callbacks
  with `ClosedError`, including tools closed with their diagram. Closing a diagram twice
  still does nothing ([#197]).
- A closed tool names its class in the `ClosedError` from `trigger()` and button clicks,
  as a closed diagram or pipe does: "ToggleCollapsedTool is closed and cannot run; build
  a new ToggleCollapsedTool". It used to say "use a new tool". `Tool.closed` says
  whether `close()` was called, like `Diagram.closed` and `Pipe.closed`. The refusal
  depends on the tool only: a tool that left a diagram's `tools` before the diagram
  closed stays open and still runs. The view's own tools, such as `Selection` and
  `FitTool`, close with the view ([#218]).
- `ElementIndex.root()`, and so `check_ids()`, `check_edges()` and `MarkIndex.root()`,
  raises `ipyelk.exceptions.NotFoundError` when every node in the index has a parent,
  and `NotUniqueError`, naming the roots, when more than one node has none. It used to
  fail an `assert` with the message "Multiple roots" for no root, and to take the first
  of several roots without a word, so the checks skipped the other trees
  ([#217](https://github.com/jupyrdf/ipyelk/issues/217)).
- Remove code that nothing used: the `ipyelk.pipes.mappings` module, the
  `GraphWrappingStrategy.horizontal` trait, and `ElkLabel.__eq__`/`__hash__`, which
  served a text sizer cache that is gone. Importing `ipyelk.pipes.mappings` raises
  `DeprecatedImportError`: nothing replaces its `Edge` and `Port` classes or its
  `NodeMap`, `EdgeMap` and `PortMap` aliases
  ([#217](https://github.com/jupyrdf/ipyelk/issues/217)).
- `ipyelk.elements.layout_options.model` keeps only the tag classes that
  `LayoutOptionWidget.applies_to` uses: `ElkGraphElement`, `ElkNode`, `ElkPort`,
  `ElkEdge` and `ElkLabel`. They have no fields, so `ElkLabel(id="l1", text="hello")`
  raises `TypeError` that names `ipyelk.elements.Label`. The generated ELK JSON data
  classes, for example `ElkPoint` and `ElkShape`, their converter functions, for example
  `from_dict`, and the `ElkRoot` and `ElkNullElement` sentinels had no users. Their
  imports raise `DeprecatedImportError`, and nothing replaces them. `strip_none` moved
  to `ipyelk.util.strip_none`. Its old import shows a `DeprecationWarning` that names
  the new place, and still works. 4.0 removes it ([#214]).
- Layout options are checked against the options that the bundled `elkjs` knows, and the
  option classes that ELK ignored without an error now take effect, so **layouts can
  change** ([#29]):
  - `EdgeSpacing`, `EdgeNodeSpacing`, `EdgeLabelSpacing`, `EdgeEdgeLayerSpacing` and
    `EdgeNodeLayerSpacing` use the `spacing.edgeEdge`, `spacing.edgeNode`,
    `spacing.edgeLabel`, `layered.spacing.edgeEdgeBetweenLayers` and
    `layered.spacing.edgeNodeBetweenLayers` ids (they used `elk.edge.*` ids that do not
    exist). Record nodes set `EdgeNodeSpacing(spacing=0)`, which now applies.
  - `LayoutPartitioning` uses `partitioning.activate` (was `partitioning.active`).
  - `ConsiderModelOrder` uses `layered.considerModelOrder.strategy` (was
    `layered.considerModelOrder`), applies only to parents, and offers `PREFER_NODES`.
  - `ContentAlignment` loses the tab character at the start of its id.
  - `PortAlignmentEast`, `PortAlignmentWest`, `PortAlignmentNorth` and
    `PortAlignmentSouth` subclass `PortAlignment`, so they have a value, a control and
    apply to nodes.
  - `LabelPortHorizontalSpacing` and `LabelPortVerticalSpacing` replace
    `LabelPortSpacing`, because ELK has no `spacing.labelPort` option.
    `LabelPortSpacing` still works, emits a `DeprecationWarning` and sets the horizontal
    spacing.
  - The `LayoutAlgorithm` choices no longer offer Draw2D
    (`org.eclipse.elk.conn.gmf.layouter.Draw2D`), because `elkjs` does not have it and a
    layout with it failed. Importing `Draw2DLayout` raises `DeprecatedImportError`
    throughout 3.x, with the algorithms to use instead in the message.
- `layoutOptions` on elements is typed `LayoutOptions` (`dict[str, str]`, from
  `ipyelk.elements`), like the ELK JSON schema. Validation writes `bool` values as
  `"true"` or `"false"` and numbers as strings. This includes the `numpy` scalars, for
  example `np.bool_`, `np.int64` and `np.float64`, and `Fraction` and `Decimal`. A
  number that is not an integer becomes a plain `float` first, so `np.float64(12.5)`
  becomes `"12.5"`. A whole-number `float` below `2**53` in magnitude loses its fraction
  (`2.0` becomes `"2"`), because ELK ignores an integer option with the value `"2.0"`. A
  larger `float` keeps the form `repr` gives it (`1e16` becomes `"1e+16"`). Validation
  raises `ValidationError` for `nan`, an infinity, `None`, any other value, or a key
  that is not a string; 2.x accepted them. Serialization writes `bool` values and
  numbers as strings too, so a value set in place (`node.layoutOptions[key] = 20`) goes
  to ELK as `"20"`. A `None` set in place makes serialization raise a
  `PydanticSerializationError` (a `ValueError`) that names the key. With
  `exclude_none=True`, serialization drops that key instead, so ELK uses the option's
  default. `OptionsWidget.value` only accepts string keys and values ([#31]).
- ELK JSON loads each shape as the class of its type string, through `convert_elkjson`,
  `from_elkjson` and the value that comes back from the frontend. So a `Path`, `Comment`
  or `Widget` keeps its class and its fields. 2.x loaded every shape as the shape class
  of its element, for example `NodeShape`. `Circle` and `Ellipse` share the type string
  `node:round`, and the JSON does not hold their radii, so a `node:round` shape loads as
  an `Ellipse` of the same size. A `node:widget` shape loads with the widget that has
  the `model_id` in `use`. If no open widget has that `model_id`, for example because
  the widget closed, ELK JSON loads the shape as a `NodeShape` with the same JSON, and
  ipyelk warns. JSON that the class of its type string rejects now raises
  `ValidationError`, where 2.x loaded it: for example a `node:path` shape without `use`,
  or a `node:widget` shape in user code with no open widget. A second shape class with a
  type string that is already taken warns and replaces the first class ([#153]).
- The elements, their properties and their shapes raise `ValidationError` (type
  `extra_forbidden`) for a key that they do not have, at construction. 2.x ignored the
  key, so a typo such as `Node(hieght=5)` did nothing. Assignment does not change. For
  an unknown key, an element and its properties already raised `ValidationError` (type
  `no_such_attribute`) in 2.x, and a shape still raises `ValueError`. The classes are
  `Node`, `Port`, `Label`, `Edge`, `EdgeSection` and their subclasses, the properties
  classes and the shape classes. A shape also rejects a field of another shape class,
  for example `Rect(start="arrow")`. `layoutOptions` stays open. ELK JSON still loads:
  `convert_elkjson`, `from_elkjson`, the value that comes back from the frontend and the
  `networkx` loader ignore the keys that the models do not have. The new
  `ipyelk.elements.from_wire(Node, data)` loads a dictionary in the same way. A `Point`
  ignores an unknown key, also in user code, and no longer raises `TypeError` for one in
  ELK JSON. The `15_Nesting_Plots` example no longer passes `key=None` to `Node`, which
  now rejects it ([#153]).
- The `use` field of each shape class has a type of its own, and the type string of the
  shape selects it, in Python, in TypeScript and in `elkschema.json` ([#148]):
  - `Comment.use` is a number of pixels (`NotchSize`), not a string:
    `Comment(use=20).use == 20.0`, and the JSON holds `20.0`. A string of a number, as
    2.x wrote it, still loads as the number. `validate_elk_json` rejects the string,
    because the schema describes the JSON of 3.0. A notch of 0 draws no notch. 2.x drew
    15 pixels for it. A notch that is not a number, is negative, `nan`, an infinity or a
    `bool` raises `ValidationError`. The renderer limits the notch to the size of the
    node.
  - The `use` of a `Path` must be SVG path data that starts with `M` or `m` and a number
    (`PathData`). The symbol identifier (`SymbolId`) of a `Use`, an `Icon`, a
    `PortShape` or a `LabelShape`, and the URL (`ImageUrl`) of an `Image`, must not be
    empty.
  - `Rect`, `Circle`, `Ellipse` and `Diamond` have no payload: their `use` must be
    `None`.
  - `Widget(widget=w, use="other")` raises: the `use` of a `Widget` is the `model_id` of
    its widget. 2.x dropped the value. Only a construction and an assignment of `use`
    check it, and not while the widget is closed.
  - Every shape validates an assignment as it validates a construction. 2.x validated an
    assignment only on `Comment`.
  - `NodeShape`, `PortShape` and `LabelShape` keep a string `use` for the payload of a
    custom shape type.
- `ipyelk.elements.Mark` and `ipyelk.elements.MarkFactory` are removed. They served the
  `networkx` transformer that 2.0 removed, and nothing used them since. Importing either
  name, or the `ipyelk.elements.mark_factory` module, raises `DeprecatedImportError`
  throughout 3.x. To load a `networkx` graph, use `ipyelk.from_nx` or
  `ipyelk.loaders.NXLoader` ([#160]).
- A `MarkElementWidget` syncs `value` with the browser only when a browser stage reads
  or writes it: the inlet of a `SyncedInletPipe`, the outlet of a `SyncedOutletPipe`
  (`ElkJS` and `BrowserTextSizer` are both), and the `source` of a viewer. These call
  the new `MarkElementWidget.sync_value()` when they take the mark. Every other mark,
  for example `Diagram.source`, keeps `value` in the kernel, so the browser no longer
  receives the tree the user built (at 100 nodes, the comm-open state of the source fell
  from 59 kB to 376 B). `flow` is never synced: no browser code reads it, and each
  refresh sends up to five fewer messages. Browser code that reads `value` of another
  mark must call `sync_value()` on it first ([#161]).
- A `Registry` holds its elements weakly, so it no longer keeps every element that it
  saw alive. A key that cannot be weakly referenced, such as a `str`, is held strongly,
  as in 2.x ([#160]).
- A `Document` (`ipyelk.elements.Document`) owns the ids of an element tree. It replaces
  the global stack of `Registry` contexts: no ipyelk code enters a `Registry` any more.
  `Document(root)` writes onto each element without an `id` the id that it serializes
  with (`wire_id`), `resolve(id)` returns a `Resolved(element, via_slack)` or `None`,
  `document[id]` returns the element or raises `NotFoundError`, `missing(ids)` lists the
  ids that do not resolve, and `lookup(ids, strict=True)` yields the elements. The index
  of a pipeline is `MarkIndex.document`, and `MarkIndex.elements` is the id map of that
  document. `MarkIndex.elements` and `MarkIndex.context` are properties now, not traits:
  `MarkIndex(elements=...)` and assignment still work, but
  `observe(callback, "elements")` never calls the callback. `ElementIndex.from_els`,
  `VisIndex.from_els` and `HierarchicalIndex.from_els` index an element without an `id`
  by its `wire_id`. In 2.x they raised `ValueError` ("Cannot index element without an
  id") outside a `Registry`. `Selection` and `Painter` resolve their ids through the
  document (the new `get_document()`), and `elements()` and `missing_ids()` keep their
  behavior. `Painter.paint(element)` stores the `wire_id` of an element that is not
  indexed yet. In 2.x it raised `ValueError` ([#160]).
- A slack port has its own id: the id of its hidden element plus `.slack` (plus another
  `.slack` while that id is in use). A slack port is the port that the projection adds
  to the nearest visible ancestor of a hidden element, so that an edge to the hidden
  element keeps an endpoint. In 2.x it had the id of the hidden element, so two elements
  had one id. Selecting a slack port still selects the hidden element:
  `Selection.elements()` returns it, and `Document.resolve` returns it with
  `via_slack=True`. The `properties.key` of the slack port is still the id of the hidden
  element. Code that compares the id of a slack port with the id of a hidden element
  must use `Document.resolve`. `Painter.paint` of a hidden element no longer styles its
  slack port, which had the same id in 2.x; paint the slack port id to style it.
  `ElementIndex.update` no longer adds the slack ports of a browser answer to the index
  ([#160]).
- An element under a second parent raises `ValueError` when it is attached, and the
  message names both parents. While the new parent is constructed, the error is a
  `pydantic.ValidationError`, which is a `ValueError` too. This applies to a label
  (`Node(labels=[label])`, `element.labels = [...]`), a child node and a port
  (`Node(children=..., ports=...)`, `add_child`, `add_port`). In 2.x a shared label
  failed later, in `ValidationPipe`, with `Nonunique Element Ids`, and a child or port
  failed an `assert` (`owned by different node`). An element that its old parent no
  longer holds attaches without an error. A label that is appended to `labels` in place
  is not checked at attach; `ValidationPipe` still reports its id.
  `Compartment(bullet_shape=...)` gives each content line its own bullet label. It used
  to share one label, which failed validation ([#160]).
- `ipyelk.elements.Registry` is deprecated and will be removed in 4.0. Constructing one
  emits a `DeprecationWarning` that names `Document` and the removal version, and a
  `Registry` keeps working through 3.x. `MarkIndex.context` is deprecated in the same
  way: reading or assigning it warns, and it holds a `Registry` that ipyelk does not
  read. This is the second tier of the 3.0 policy: a name that worked warns and keeps
  working, and a name that never worked raises. The `11_Logic_Gates` example uses
  `Document` ([#160]).
- `MarkIndex` is a plain `traitlets.HasTraits`, not a widget. It opens no comm and no
  `Layout`, and `MarkElementWidget.index` is never sent to the browser. Every stage
  outlet of a pipeline shares the index of the pipeline's inlet, and the index is built
  on first read, so one `Diagram()` builds no index that it throws away.
  `MarkElementWidget` is a `Widget`, not a `DOMWidget`, because no view displays it.
  Thus, it has no `layout`, and its browser model is a `WidgetModel`. One `Diagram()`
  opens 52 widgets, not the 78 of 2.1.1. These uses break: a `MarkIndex` used as a
  widget (`.comm`, `close()`, `display()` or `widget_serialization`), browser code that
  reads `mark.get('index')`, and code that reads `layout` of a `MarkElementWidget`.
  `MarkIndex.comm`, `MarkIndex.close` and `MarkElementWidget.layout` raise
  `DeprecatedAPIError` throughout 3.x. The index stays shared:
  `source.index.elements = None` makes the next run rebuild it, as in 2.x ([#237]).

#### Migration

To change 2.x code for 3.0, read [Migrating from ipyelk 2.x to 3.0][migration]. It has a
section with the 2.x code and the 3.0 code of each breaking change above. Its [table of
removed names][migration-removed-names] lists every name that raises
`DeprecatedAPIError` or `DeprecatedImportError`, with a link to its section.

#### Added

- `Viewer.fit_on_first_layout` (default `False`) makes each view fit the whole diagram
  in the browser after its own first layout. `Viewer.fit()` is a message to the views
  that exist when it is sent, so a diagram displayed after it was laid out opened at 1:1
  in the top-left corner, and so did every later view of it. A view that is hidden at
  its first layout (in a collapsed accordion or a background tab) fits the first time it
  is shown. Each view fits once: later layouts (a new `source` included), reveals and
  resizes keep its camera, a view laid out before the trait was set is not fitted, and a
  `set_viewport()` sent while a hidden view waits cancels its fit. `Viewer.fit_padding`
  (default `0`, in diagram units) and `Viewer.fit_max_zoom` (default `None`: only the
  viewer's own limit of 10) set the padding and zoom limit of that fit, and of `fit()`
  calls and Fit button clicks that pass none ([#245]).
- `Node.clone(prefix)` copies a node with everything under it, for a fragment that is
  used in several places. The copy of an element with the id `X` has the id
  `"<prefix>.X"`, where `X` is the id or the `wire_id` of the original. So two clones
  with one prefix get the same ids if they copy the same fragment object, or a fragment
  whose elements all have an `id`. An element without an `id` gets a new `wire_id` each
  time its fragment is built again, and so does its copy. The copies have their own
  parents, `layoutOptions` and `properties`. Edges inside the fragment connect the
  copies, and an edge to an element outside the fragment keeps that endpoint. `metadata`
  and the widget of a `Widget` shape are shared ([#160]).
- An opt-in check for layout option keys that ELK ignores without an error. ELK takes a
  full option id, or the end of one that starts after a dot (`elk.direction`,
  `spacing.nodeNode`), and the old ids of some options (`layered.northOrSouthPort`).
  `ipyelk.schema.unknown_layout_options(keys)` returns the keys that end no id or more
  than one: `direction` also ends `layered.priority.direction`.
  `ipyelk.schema.untargeted_layout_options(keys, targets)` returns the keys whose option
  does not apply to that kind of element, for example a node option on an edge.
  `ValidationPipe(check_layout_options=True)` writes them per element id to
  `layout_options_report` and `layout_options_target_report`, and emits one
  `UserWarning`. The check is off by default, and turning it off clears both reports.
  Refs [#115].
- Allow diagram construction without a running event loop. `Pipe.schedule_run()` and
  `Diagram.refresh()` return `None` when they cannot schedule a task.
- Add optional `LabelProperties.tooltip` and `LabelProperties.separator` fields.
- Re-send widget state after a browser reports missing state, with throttling.
- Echo terminal progress state twice, cancelling pending echoes on updates and close.
- Surface pipe/diagram exceptions via an `on_error` callback instead of silently
  dropping them in the asyncio done-callback (F4)
- Add a configurable `timeout` and a browser→kernel error channel to
  `ElkJS`/`BrowserTextSizer` so a failed or silent browser layout no longer hangs the
  diagram (F6)

#### Fixed

- PyPI shows the license: the wheel and the source distribution declare
  `License-Expression: BSD-3-Clause AND EPL-1.0 AND EPL-2.0` (PEP 639), because the
  package contains code under each of these licenses, and list `LICENSE.txt`,
  `COPYRIGHT.md` and the Eclipse Public License (EPL) 1.0 and 2.0 texts as
  `License-File`s, which the wheel ships under `.dist-info/licenses/`. 2.1.x had only a
  `License ::` classifier, so PyPI showed no license. The bundled elkjs and sprotty
  packages are available under EPL-2.0, and some source files are derived from EPL-1.0
  or EPL-2.0 code: `COPYRIGHT.md` names the license of each. The npm package's
  `package.json` declares the same expression. `scripts/check-dist.py` fails the build
  if the expression changes, if these fields or files go missing, or if `dist/` does not
  hold exactly one wheel and one source distribution of this version. The PyPI
  `Changelog` link points at the `master` branch ([#133])
- Hiding a root-level node with visible edges no longer crashes elkjs: `iter_visible`
  reported every sibling after a hidden one as hidden and projected a hidden node's
  slack port onto its preceding sibling (for a hidden first child of the root, onto the
  root itself, which elkjs rejects). Hidden compound children now project onto the
  compound, and an edge whose projection would touch the root is dropped from the wire
  while its `Edge` stays in the index (#161, #169)
- Never serialize an id as `null`: an id-less element mints a wire id once and keeps it,
  the index adopts it, and an id the `Registry` mints first becomes the wire id, so
  edges no longer go on the wire as `sources: [null]` and the id first seen is the id
  for the object's life. Port ids compose from the parent's id in and out of a
  `Registry` (was `<uuid>.<uuid>` under `Node(id="N")`), a copied element mints its own
  wire id instead of sharing the original's, and `Label.wrap` no longer copies a
  generated id onto every line (#160, #169)
- Add nested label spacing regardless of the sublabel width: `size_nested_label` parsed
  `ls.width or 0 + spacing` as `ls.width or (0 + spacing)` (#161, #169)
- Stop echoing browser-written state back to the frontends: the selection, the hover and
  the laid-out graph were re-sent to every attached frontend as soon as the browser
  wrote them, and the graph was then sent a _second_ time as a re-serialized copy, so
  every layout arrived back twice and the diagram re-rendered on each. Known limitation,
  documented on the traits: a second frontend attached to the same kernel no longer
  learns browser-made selections from that echo ([#164], [#161])
- Keep a refresh that was requested while a run was already in flight: a style change,
  or a tool that failed after changing the model, recorded itself by overwriting the
  pipeline's pending flow, and a completing run cleared that flow by overwriting it in
  turn — so the request was lost and the change never redrawn. Runs now _take_ the
  pending flow when they start and put it back if they fail or are cancelled ([#164],
  [#160])
- Stop throwing away browser work a refresh has already started: a burst of `refresh()`
  calls cancelled the in-flight run and started another, so the browser went on laying
  out graphs whose results were discarded, and a cancelled run's answer could be
  consumed by its successor. Requests are now counted rather than cancelled and one
  runner serves them on the trailing edge (ten calls in one tick cost one layout), and
  each roundtrip carries a generation counter, so a re-sent request is recognized as the
  same work instead of queueing a duplicate layout in the browser and an answer for an
  abandoned generation is ignored. `Pipe.cancel()` is now the only thing that stops a
  run, and `pipe._task` is the pipe's current runner rather than "the run this call just
  scheduled" ([#164], [#161])
- Stop swapping the browser's laid-out copy into the pipeline's input: it carried
  nothing that persisting the result does not already merge into the user's own
  elements, but the next run rebuilt the element index from that copy, so a selection
  resolved to a copy and a hidden node resolved to the slack port sharing its id
  ([#164], [#161])
- Make edge-owner validation linear in the hierarchy instead of quadratic in it:
  validating 1000 nodes with 3000 root-owned edges fell from 14.4 s to 0.010 s (500
  nodes / 1500 edges, 3.5 s to 0.005 s; 100 / 300, 0.146 s to 0.001 s), and validation
  no longer re-reports on its outlet when it changed nothing ([#164], [#161])
- Settle a browser roundtrip on the event loop that awaits it: with `ipykernel` 7 and a
  frontend that uses kernel subshells (JupyterLab 4.5+, ipywidgets 8.1.8+), widget
  messages are handled on a subshell thread with its own loop, so an answer written from
  there did not wake a run started from a cell until the resend timer fired, and a
  `refresh()` from a widget callback reused a runner from the other loop and failed
  silently. Answers are now delivered through the future's own loop, and a refresh from
  another loop hands the runner over to the caller's loop ([#164])
- Stop leaking widgets on every refresh. Each pipe status change created a new
  `PipeStatus` widget, and a displayed pipeline status view rebuilt its rows. Neither
  closed what it replaced: 9 widgets leaked per refresh, 145 with the view shown. The
  status view now rebuilds its rows only when the sub-pipes or their views change, and
  closes the rows it replaces ([#176])
  - `PipeStatus` is no longer an `ipywidgets.Widget`: it is an immutable value with the
    same attributes and constructors, compared by identity, so every new status still
    notifies `status` observers
  - `PipelineStatusView.statuses` is removed. It held the view's row widgets, was never
    synced, and is now a private list; the rows still reach the frontend as `children`
- Close the old pipeline when `diagram.pipe` is replaced. Only its run was cancelled:
  its sub-pipes, intermediate marks and status views stayed open, and the diagram's
  `style` link kept it alive, so every replacement left 37 widgets behind, 99 with the
  status view shown. A diagram now owns its pipe: replacing it closes the old pipe, its
  sub-pipes and the widgets they created (including a `status_widget` displayed
  elsewhere), never `diagram.source` or an inlet/outlet passed in. `Pipe.close()` closes
  what the pipe created (a `Pipeline` also closes its sub-pipes). `style` (also for a
  text sizer in a nested pipeline), the progress bar and the tools now follow the new
  pipe ([#180])
  - A pipe belongs to one diagram, with every pipe nested in it. Assigning a pipe that
    nests a pipe another open diagram owns raises `TraitError`: both diagrams used to
    share its outlet, so one silently showed the other's graph. Two diagrams sharing a
    _source_ is a separate question ([#178])
  - A replaced pipe is closed, so assigning a pipe that nests a closed pipe, or any part
    of the current pipe (wrapping it, or reusing its stages), raises `TraitError` too:
    build a new pipe instead
  - The rule also holds when a pipeline's `pipes` changes in place, and before a
    `Pipeline` is wired. Adding another open diagram's stage to an assigned pipeline was
    accepted, so the stage ran in both, and `Pipeline(pipes=[...])` rewired a live
    diagram's stage before anything could refuse it. Both now raise `TraitError` and
    change nothing, as does a `pipes` list with a closed stage or a stage listed twice
    (it was wired into a cycle). A stage added in place belongs to the diagram (and gets
    its `style`); a stage removed in place is released, not closed ([#191])
- Close what a diagram owns when the diagram is closed. `Diagram.close()` only released
  its pipe, so the pipe tree, the view, the tools and the toolbar stayed open: every
  closed diagram left 68 widgets behind, 130 with the status view shown. It now closes
  them with their layout and style widgets and drops its links to them, and leaves open
  `diagram.source`, an inlet or outlet passed to a pipe, the viewer's `control_overlay`,
  and a `layout` or tool `ui` passed in. A closed diagram's pipe is closed, so another
  diagram can no longer take it. `Tool.close()` also closes the `ui` the tool built, and
  `Viewer.close()` its tools ([#191])
- Log the routine "fixing N ids" message from `ValidationPipe` at debug level instead of
  warning: assigning ids to id-less elements is the normal path (`fix_null_id=True`), so
  every diagram built from id-less elements logged it
- Keep the elements behind a collapsed view intact across layouts ([#171], [#187]):
  - A hidden port, or a port on a hidden node, keeps its size, position, layout options
    and properties. The slack port that stands in for it in the layout used to overwrite
    them with its own 5×5 geometry, permanently. Any other port, including one that
    moved to another node, still takes its layout from the browser.
  - Each line of a wrapped label gets its own ids, and so do its sub-labels. The lines
    of a label with id `L` get the ids `L#0`, `L#1`, … (sub-label `sub` gets `sub#0`,
    …). If another element already uses one of these derived ids, indexing gives that
    line a fresh id; ids you set yourself never change. Before, every line had the same
    id (`L`, or one generated id) and the same sub-label ids. A wrapped line shares its
    label's `metadata`.
  - The ELK JSON schema accepts the slack-port `key` and `hidden` properties, so a
    projection validates after a collapse and an expand.
- Center a `Circle` in its node: `Circle` no longer serializes `x` and `y` as its
  `radius`. The `node:round` renderer takes its radii from the laid-out node, so a node
  larger than the circle drew the ellipse off center. `x` and `y` that you set are still
  serialized ([#200])
- Keep a typed shape through a layout round trip. `ElementIndex.update` replaced every
  element's `properties` with the browser's copy, whose shape parses as the base class:
  a `Circle` came back as a `NodeShape` without its `radius`, an `Icon` as a
  `LabelShape`, a `Widget` without its widget, and `shape.radius = 20` then raised. The
  frontend never changes `properties`, so an element now keeps its own, with its shape
  object, and an edit made while a layout was in flight is no longer reverted. The
  laid-out `width` and `height` are still written onto the element, where you can read
  them, but no longer shadow the shape's size in the input to the next layout: a
  `radius` set after a layout resizes the node at the next one, and a `LabelShape` that
  sets only `width` now sends that width, not the measured one, starting with the first
  layout. A `width` or `height` assigned to a `Label` is now sent to the layout instead
  of the measured size, starting with the first layout. A size assigned to the element
  itself stays the input to every later layout and wins over the shape ([#201])
- Find an existing port when a NetworkX edge's `sourcePort`, `targetPort` or `port` is
  the port's global id rather than its key. `ElementIndex` had no `__contains__`, so the
  loader's `port_key in el_map` check was always false and it added a second port with
  that key instead. `ElementIndex` and `HierarchicalIndex` now support `key in index`,
  by id. A key that is the id of anything other than one of the endpoint's own ports
  still makes a new port with that key, as before ([#215])
- `from ipyelk.elements import *` works. Its `__all__` named `ElementShape`, which the
  package did not import, and `check_ids`, which is an index method. Ruff rule `F822`
  (an undefined name in `__all__`) is on now, and a test star-imports every module that
  has an `__all__` ([#217])
- Stop `Record` from making six widgets for each child every time it is serialized, on
  every synced `value`, and never closing them: it writes the same size option strings
  to its children without the option widgets. A `min_height` that is not a whole number
  still fails to serialize, now with a `ValueError` that names it, where the widget's
  `Int` trait raised a `TraitError` ([#217])
- Export the wrapping layout options `GraphWrappingStrategy`,
  `AdditionalWrappedEdgesSpacing` and `CorrectionFactorForWrapping` from
  `ipyelk.elements.layout_options`: no module imported them ([#217])
- `Diagram.register_tool` binds each dependency in the tool's `_dependencies` that the
  diagram supplies (`diagram`, `pipe`, `view`, and the view's `selection`, `hover`,
  `viewport` and `painter`), and still binds a `diagram` or `selection` trait that a
  tool does not list. A `PipelineProgressBar` added this way is bound to the pipe, and
  gets the progress reports when no other bar has them. A bar moved from another diagram
  stops getting the reports of that diagram's pipe ([#217])
- `logic_gates.Gate` passes `minimum_size` (it was `minimun_size`, which `traitlets`
  dropped with a warning). The text sizer sets the style CSS as the text of its
  `<style>` element, not as markup ([#217])
- `iter_labels` yields every label of each element and its child nodes, each element's
  own labels first. It yielded only the first label of each element ([#217])
- Fix `IDReport.message()` printing literal `{eid}`/`{el}` placeholders (F1)
- Fix `Pipeline.check()` / `get_progress_value()` crashing on an empty pipeline (F2)
- Give each `Tool` its own `on_run` callback dispatcher (was shared across all tools)
  (F3)
- Re-send the browser `run` request with backoff until a frontend answers, so a pipe run
  before its diagram is displayed no longer waits on a message nobody received; a
  browser-reported layout error stops the retries immediately (F10)
- Treat an errored run as terminal for progress reporting: `PipeStatus.step()` returned
  `None` for errored pipes, so `Pipeline.get_progress_value()` raised `TypeError` inside
  the error path — `on_error` saw the `TypeError` instead of the layout error, and the
  `PipelineProgressBar` sat "in progress" forever; the bar now fills as a visible
  warning (F10)
- Keep hidden elements in the shared `MarkIndex` across browser round trips:
  `Node.dict()` always drops hidden children, so rebuilding the index from a value that
  has been through the browser erased them and `ToggleCollapsedTool` could never reveal
  them again — nested widgets (such as the `15_Nesting_Plots` figures) never appeared.
  `ElementIndex.update()` now merges instead of requiring every id to be known: existing
  ids update in place, unknown ids are added, which also fixes a `NotFoundError` when
  slack ports introduced by `VisibilityPipe` come back from a layout (F12)
- Log a failed layout in `Diagram.refresh()` instead of returning silently: a silently
  failed pipeline is indistinguishable from a hung diagram (F12)
- Fix the local `TextSizer` fallback, which read `self.source.value`, assigned
  `self.outlet.changes` and returned `self.value` — none of which exist on `Pipe` — and
  therefore raised on its first statement (F13)
- Do not wait on a browser that cannot answer: with `IPYELK_NO_BROWSER` set (as
  `nbconvert --execute` does) a pipe gives up its roundtrip immediately instead of
  keeping a task alive across cell boundaries re-sending `run` requests for 30 s, which
  wedged kernels on slower CI runners (F15)
- `NXLoader` finds the owner of each edge by walking up the parents of its two ends, not
  with `networkx.lowest_common_ancestor`, which searches the whole hierarchy for each
  edge. The owners do not change. Loading a random tree of 3,000 nodes and 3,000 edges
  falls from 3.3 s to 0.4 s. A cycle in the hierarchy still raises a `NetworkXError`,
  which now names the cycle. It raises also if no edge joins two different nodes, where
  the loader dropped the nodes of the cycle ([#160])
- `NXLoader` raises a `NetworkXError` that says the hierarchy must be directed, for an
  undirected hierarchy such as an `nx.Graph`. It raised
  `NetworkXNoCycle: No cycle found.`, which did not name the problem ([#160])
- Only ELK JSON loads a `node:widget` shape with no open widget for its `use` as a
  `NodeShape`, with a warning. Such a dictionary in user code, for example
  `NodeProperties(shape={"type": "node:widget", "use": "x"})`, raises `ValidationError`,
  as `Widget(use="x")` does. Before, it loaded as a `NodeShape` and warned, as ELK JSON
  does ([#153])

### Development

- Skip a failing `04_Interactive` (tag `gh:95`) only on macOS `test`, where the kernel's
  slider values still lag the browser now and then ([#232]). `test-oldest` on Ubuntu and
  macOS passed it in every finished run since the #177 fix, so a failure there fails the
  job again
- Check the source maps in the wheel: `scripts/check-dist.py` fails unless every
  labextension `static/*.js` has a `.map` beside it and ends with a `sourceMappingURL`
  that names it, and unless the maps hold the TypeScript (`sourcesContent`) of every
  `js/` file that compiles to runtime code. A change to the JS build can no longer drop
  them without notice ([#83])
- `src/ipyelk/schema/elk-catalog.json` lists the layout options, algorithms and
  categories of the bundled `elkjs`. `pixi run build-py-elk-catalog` writes it. A
  `vitest` checks it against the installed `elkjs`, and a unit test checks the option
  classes against it ([#29]).
- CI also regenerates `elk-catalog.json` and fails if it differs from the committed
  file, and `jlpm schema` passes the real path of `elkschema.ts`
  ([#187](https://github.com/jupyrdf/ipyelk/issues/187)).
- A unit test checks the models against `src/ipyelk/schema/elkschema.json`, which the
  TypeScript types of the frontend generate. Every key that a model, or a subclass in
  `ipyelk`, can write must be in the schema. A graph with every kind of element, every
  shape and hidden elements must validate, as the view gets it and as ELK gets it. The
  view types that `js/sprotty/di-config.ts` registers must be the type strings of the
  shape classes and four types that only the frontend uses: `graph`, `junction`,
  `symbol` and `node:compartment`. The pipeline does not validate: on 1000 nodes,
  validation takes about 5 times as long as the serialization that it checks. To check a
  payload while you debug, call `ipyelk.schema.validate_elk_json(to_json(node, None))`
  ([#131], [#153]).
- Add `scripts/bench_pipeline.py`, a headless benchmark of `Diagram.refresh()`: it runs
  the real kernel pipeline and real `elkjs` in `node` with only the two browser stages
  stubbed, over deterministic graphs from `scripts/bench_graphs.py`, and reports wall
  and per-stage time, comm messages and bytes in both directions, layout runs, a
  collapse refresh and a ten-refresh burst ([#164], [#167]), and the comms opened per
  refresh ([#176])
- Gate CI on the benchmark's deterministic counts: `pixi run bench-check` compares them
  to `scripts/bench_baseline.json` and fails on any change until the baseline is updated
  with `pixi run bench-update` ([#176]), including the live widgets left by replacing
  `diagram.pipe` ([#180]) and by closing a diagram ([#191])
- Run the benchmark on the oldest supported ipywidgets too: on 8.0.1 it crashed in its
  first refresh, because ipywidgets 8.0 opens an `ipykernel` comm directly and the
  harness never saw a message. `pixi run bench-check-oldest` gates it against the same
  baseline in the `test-oldest (ubuntu-latest)` job ([#191])
- Add `ast-grep` structural lint rules for Python and TypeScript (`sgconfig.yml`,
  `scripts/ast-grep/`), each with test cases, run by `pixi run lint-ast-grep` as part of
  `pixi run lint`; a suppression must name its rule and still match something ([#147])
- Lint prose with Vale in the `lint` job: `pixi run lint-vale` checks US English
  spelling and the `proselint` and `write-good` styles in the root `*.md` files,
  `docs/`, docstrings and comments in `src/`, `tests/` and `scripts/`, and notebook
  markdown, and fails on any warning or error. It replaces `check-spelling`, which
  linted the built HTML and never failed ([#181])
- The nbconvert kernel watchdog writes its stack dump to the kernel's real stderr, not
  to the descriptor ipykernel captures, where the dump woke the capture thread and made
  it look busy. A second dump lists the pending `asyncio` tasks of the kernel's event
  loops, with their await chains, and whether the shell locks are held ([#177])
- Fix the `itest-nbconvert` hang in `03_App.ipynb` ([#177]). ipykernel 7.0 to 7.3 send
  shell replies raw on the socket their shell stream reads from, which can swallow the
  wake-up for a request that arrives during the send. The request then waits unread
  while the kernel idles. In nbconvert that happens when a cell prints into an
  `ipywidgets.Output`: `nbclient` answers with a `comm_msg` just as the cell's reply
  goes out, and the next cell never runs.
  - The `itest` and `atest` environments now lock ipykernel 7.4, which fixed it
    ([ipykernel#1529]).
  - ipykernel 7.4 needs Python 3.11 or newer. For the Python 3.10 environments, the
    kernels of the `nbconvert--` task and of the robot tests load
    `scripts/kernel_shell_reply_fix.py`, a startup file that backports the fix and does
    nothing on ipykernel 7.4 or newer. `utest-oldest` tests it
- Lower the `nbconvert--` cell timeout from 1200 s to 40 s. The slowest healthy notebook
  in 4061 notebook runs from the last 45 CI runs took 8.2 s. The kernel watchdog now
  restarts with every cell and fires after 30 s without a new cell ([#177])
- Fail CI when the committed `elkschema.json` differs from what `jlpm schema` generates,
  and rebuild it when `elkgraph-json.ts` changes ([#187])
- Run the JS unit tests that need a DOM under `happy-dom`, chosen per file with a
  `@vitest-environment happy-dom` comment ([#216])
- Fail the `lint` job when `pixi run fix` changes a committed file or adds a file that
  git does not ignore (`git diff --exit-code`, `git status --porcelain`), and commit
  what it changes: `taplo` also formats `scripts/*.toml`, and `ATEST_ARGS` in `ci.yml`
  is a literal block, which `prettier` leaves alone. Ruff targets Python 3.10, the
  `requires-python` floor. `jlpm clean` keeps the committed `elkschema.json`.
  `CONTRIBUTING.md` names `pixi run watch-js` and `.github/workflows/ci.yml` ([#217])
- Track every work marker: a `TODO`, `FIXME`, `XXX` or `HACK` comment names its issue as
  `TODO(#123): what to do`, as `CONTRIBUTING.md` describes. `scripts/check_todos.py`,
  run by `pixi run lint-todos` as part of `pixi run lint`, fails on a marker in code
  that names no issue, and on a `todo:` or `fixme:` in lower case. Delete the obsolete
  markers, and file an issue for each of the others ([#217])
- Skip the `16_Cervidae_Tree` notebook tests, with the reason, when
  `examples/data/cervidae-tree.zip` is a git-lfs pointer file: a clone without git-lfs
  failed them with `BadZipFile` ([#217])
- Test the oldest environment on Firefox 153 ESR, the current ESR line, instead of 128
  ESR, which is no longer updated. 140 ESR reached end of life on 2026-10-13, and
  crashes at launch on macOS arm64 (`binary is not a Firefox executable`). It is not yet
  known whether this changes the out-of-memory kills of `01 Linking` and
  `02 Transformer` in `test-oldest (ubuntu-latest)` ([#199])
- Migrate to native Pydantic 2 validation and serialization; require
  `pydantic >=2.12,<3`. Use `model_dump()` / `model_dump_json()` instead of `dict()` /
  `json()`. Custom models now use `model_config`, `Field(exclude=True)`, and native
  serializers instead of `Config`, `merge_excluded`, and `dict()` overrides. Nested
  subclass fields and graph references are preserved; shape serialization no longer
  mutates dimensions. Explicit serialization field selections are now respected.
- Fix Python typing throughout the package and run mypy as part of `pixi run lint`.
- Minimum supported Python is now `3.10`
- Upgrade the pinned `pixi` from `0.34.0` to `0.67.0` (and `setup-pixi` to `v0.10.0`);
  relocking updates `libgfortran5` `13.2.0`→`14.2.0`, fixing a macOS arm64 dyld failure
  that broke `numpy`/`bqplot` in the example notebooks
- Only reinstall requirements in the `07_Simulation` example when `ipyelk` is missing,
  and add `tooltip`s to its control widgets
- Preserve the normal labextension in `src/_d` during the coverage build
  (`build-js-ext-cov`), which emptied it and left `pixi run build` with an unloadable
  extension (`_build.load: "static"`)
- Test that the browser text sizer adds its listener for font loads once for each
  `FontFaceSet`, also with two sizer models that each run twice ([#161])

### Documentation

- Add the page [Migrating from ipyelk 2.x to 3.0][migration] (`docs/migration.md`),
  linked from the README and the docs index: a section for each breaking change, with
  the 2.x code, the 3.0 code and the error or symptom that the 2.x code shows on 3.0.
  Tests check the page against the code and the CHANGELOG ([#219])
- Document the shape API: a docstring for each class in `ipyelk.elements.shapes`, and a
  _Shapes_ page in the API reference with one table row for each shape ([#66])

### `@jupyrdf/jupyter-elk 3.0.0-alpha0`

- Fit each view after its first layout when the viewer's `fit_on_first_layout` is set:
  every element of the layout (ports and labels outside their parent included, and not
  narrowed to a selection), without animation, with the viewer's `fit_padding` and
  `fit_max_zoom`. A layout with no sized node does not count as the first. A view with
  no size on the page then waits for an `after-show` or `resize` message or a
  `ResizeObserver` callback (a CSS reveal), and stops observing once it fits, is
  removed, or a `viewport` command addressed to it arrives ([#245]).
- Write `hovered_id` back on pointer leave, but only when the departed element is still
  the hovered one, so a stale leave cannot erase a newer enter; never dispatch `null` to
  sprotty as an element id; re-wiring the hover tool releases the previous tool's
  listener ([#155]).
- Skip the control overlay when the viewer's `control_overlay` is `null` or has no
  `children`, and re-render when its `children` change ([#156]).
- Report the viewport: every `ELKViewerView` owns a stable `view_id` and, 100 ms after
  the last `SetViewport`/`Center`/`FitToScreen`/`InitializeCanvasBounds` action (plus
  sprotty's animation time for an animated move) or re-layout, writes `view_id`,
  `origin`, `zoom`, `canvas_size` and `viewed_ids` to the kernel's `viewport` tool in
  one state update. A gather superseded by a newer one is dropped, a snapshot the kernel
  could not tell from the last write is skipped, and a detached view never reports. The
  `viewport` custom message applies `SprottyViewer.set_viewport` to the addressed view
  (or every view) ([#156]).
- Apply the kernel `painter.styles` at transform time: the ELK -> sprotty transform
  merges the painted classes after each element's model classes (no duplicates, symbols
  excluded), so every render -- including re-layouts -- carries them, and a
  `change:styles` re-renders the same layout through sprotty's model update, which keeps
  the selection and the camera. `UpdateModelCommand2` now also carries `hoverFeedback`
  over to the updated element, so a re-render under a resting pointer no longer drops
  the mouseover ([#156]).
- Remove `NodeExpandTool` and its `ExpandAction`: its `wheel` handler returned before it
  did anything, and nothing sent the action. Remove the empty `change:interaction`
  listener too: no kernel class has an `interaction` trait
  ([#217](https://github.com/jupyrdf/ipyelk/issues/217)).
- Fix the first-frame culling bug while culling stays off: `validCanvasBounds` was the
  inverse of its comment, so nothing was culled on a sized canvas and almost everything
  on the `0x0` canvas before the first `InitializeCanvasBoundsAction`; the guard now
  skips culling while the canvas size is unknown, behind an explicit `CULLING_ENABLED`
  constant (turning it on is #170). The SVG exporter sizes its `viewBox` from the
  model's content extent instead of the live group's bounding rect, which under-sized by
  the layout's left margin and made the export viewport-dependent (#161, #169)
- Stop a diagram from freezing for good on an update that removes elements. Sprotty's
  fade-out removed the faded elements when the _eased_ animation time reached 1, which
  `easeInOut` rounds to within 1e-8 of the end, while the animation only stops at the
  _raw_ time 1. A frame landing a hair before the end (evenly spaced frame timestamps,
  15 frames of 1000/60 ms for the 250 ms animation) removed them early, and the real
  last frame removed them again and threw. The throw happened inside an animation-frame
  callback, so the animation never finished and sprotty's command stack waited on it
  forever: every later layout reached the browser and was never drawn ([#95]). Reported
  upstream as [eclipse-sprotty/sprotty#573]; the workaround can go once that is fixed
- Offset a label icon vertically by its `y`, not its `x`: `ElkLabelView` added
  `icon.position.x` to the icon's `y`, so an icon's `x` also shifted it down and its `y`
  was ignored ([#205])
- Stop selecting a widget node on a click inside its widget, such as on the handle of a
  slider or the icon of a button: such a click is a widget click, which the select tool
  ignores, wherever it lands in the widget. Before, only a click on the widget's own
  element counted, so a widget node could be selected by clicking its widget's contents
  and no longer can. A diagram shown as a widget node of another diagram still selects
  its own nodes, and the outer diagram no longer selects the node that shows it ([#216])
- Add optional label tooltips and full-width separators above labels.
- Observe source rewiring and apply initial kernel selections after model submission
  completes.
- Report missing browser state for re-sync and surface text-measurement errors through
  the kernel error channel.
- Discard widget views whose attachment host disappears while they load.
- Attribute label hover feedback to the nearest hoverable element.
- Fix the SVG exporter `enabled` flag, which was always `true` (F5)
- Report browser-side layout failures to the kernel instead of silently emitting an
  empty layout (F6)
- Make `ELKLayoutModel.layout()` re-entrant: it stripped element `properties` (incl.
  `cssClasses`) off the shared inlet value in place, so a duplicate `run` message or an
  overlapping refresh re-laid-out the stripped graph and pushed a style-less
  (black-and-white) diagram (F7)
- Render edge labels where ELK placed them: `ElkLabel` carried sprotty's
  `edgeLayoutFeature`, whose EdgeLayoutPostprocessor re-anchors edge labels along the
  route and treats ELK's absolute coordinates as a relative offset, shifting every edge
  label by roughly its edge's origin (F8)
- Orient edge end symbols along the visible route: the adjacent-segment tangent
  collapsed to `atan2(0, 0)` on the duplicated control points of elkjs `SPLINES`
  sections (arrowheads drawn 180° wrong, inside the target node) and followed the short
  exit stub of `POLYLINE` routes instead of the visible diagonal; interior bends under a
  symbol's footprint no longer make the trimmed shaft double back (F9)
- Drop the selection write-back race: `getSelection()` resolves one action-queue slot
  later, so two `SelectAction`s dispatched close together each read the _other_ action's
  resulting state and wrote it back, flipping the selection tool's `ids` forever — a
  self-sustaining oscillation that pegged the renderer's main thread (F11)
- Render nested JupyterLab widgets in the pass that reveals them: the overlay was built
  from a registry populated by the _previous_ render's `snabbdom` hooks, so a widget
  node that had just become visible produced no container until some later, unrelated
  re-render happened to run (F14)
- Make the selection write-back set-based so linked views cannot bounce: F11's
  generation stamp is per view, but `change:ids` is observed by every view of a shared
  model, and each view gathers the same selection in a different order, so a reordering
  kept dispatching `SelectAction`s between two views until the browser ran out of memory
  (F16)
- Add a `vitest` unit-test harness (F5)
- Upgrade ELK.js from `0.9.3` to `0.12.0` ([#140]). `ElkEdge` gains an optional
  `container` field in the generated schema, and a `vitest` lays out a graph with the
  real bundle to pin the port, edge-section and `properties` round-trip contract.
- Upgrade `sprotty` and `sprotty-protocol` from `1.3.0` to `1.4.0`, which requires
  `inversify ^6.1.3` (pinned to `6.2.2`) and `reflect-metadata ^0.2.2`. The `inversify`
  shared module declares its `version` statically: its `lib/esm` entry ships a
  version-less `package.json`, so webpack module federation would otherwise register it
  as `0` and warn on every page load; a unit test keeps the static version exact, equal
  to the dependency pin and inside the declared `requiredVersion`.
- Drop the unused `sprotty-elk` dependency: nothing in `js/` ever imported it, `sprotty`
  and `sprotty-protocol` do not depend on it, and the built extension has no reference
  to it. Its `elkjs ^0.8.2` range was the only thing that conflicted with ELK.js
  `0.12.0`, so the `resolutions.elkjs` override goes with it ([#140]).
- The browser text sizer measures a label again only if its text or its CSS classes
  change, or the CSS of the sizer or the label font of the theme, or after the page
  loads a font. It keeps the 0 size of a label with no text. It measured every label on
  every run: it skipped only a label whose shape has a size, and it writes the size onto
  the label, not onto the shape. A run with no label to measure answers at once, without
  the DOM ([#161])
- Bundle `elkjs/lib/elk-worker.min.js`, the compact build of the elkjs worker, not
  `elk-worker.js`. The worker in the lab extension falls from 1.92 MB to 1.46 MB, and
  its source map from 7.7 MB to 4.2 MB. This makes the wheel about 0.4 MB smaller
  ([#161])
- `Shape` is a union of one interface for each built-in type string, for example
  `CommentShape` and `PathShape`, and `CustomShape` for the other type strings. Each
  interface gives `use` its type. `shapeOf<T>(element)` reads the shape of an element as
  the variant of its view. The comment view draws no notch for 0, and limits the notch
  to the size of the node. A notch that is missing, not a number or negative draws 15
  pixels, and a string notch from 2.x still draws ([#148])

[#29]: https://github.com/jupyrdf/ipyelk/issues/29
[#31]: https://github.com/jupyrdf/ipyelk/issues/31
[#66]: https://github.com/jupyrdf/ipyelk/issues/66
[#83]: https://github.com/jupyrdf/ipyelk/issues/83
[#95]: https://github.com/jupyrdf/ipyelk/issues/95
[#115]: https://github.com/jupyrdf/ipyelk/issues/115
[#131]: https://github.com/jupyrdf/ipyelk/issues/131
[#133]: https://github.com/jupyrdf/ipyelk/issues/133
[#140]: https://github.com/jupyrdf/ipyelk/issues/140
[#147]: https://github.com/jupyrdf/ipyelk/issues/147
[#148]: https://github.com/jupyrdf/ipyelk/issues/148
[#153]: https://github.com/jupyrdf/ipyelk/issues/153
[#155]: https://github.com/jupyrdf/ipyelk/issues/155
[#156]: https://github.com/jupyrdf/ipyelk/issues/156
[#160]: https://github.com/jupyrdf/ipyelk/issues/160
[#161]: https://github.com/jupyrdf/ipyelk/issues/161
[#164]: https://github.com/jupyrdf/ipyelk/issues/164
[#167]: https://github.com/jupyrdf/ipyelk/issues/167
[#171]: https://github.com/jupyrdf/ipyelk/issues/171
[#176]: https://github.com/jupyrdf/ipyelk/issues/176
[#177]: https://github.com/jupyrdf/ipyelk/issues/177
[#178]: https://github.com/jupyrdf/ipyelk/issues/178
[#180]: https://github.com/jupyrdf/ipyelk/issues/180
[#181]: https://github.com/jupyrdf/ipyelk/issues/181
[#187]: https://github.com/jupyrdf/ipyelk/issues/187
[#191]: https://github.com/jupyrdf/ipyelk/issues/191
[#197]: https://github.com/jupyrdf/ipyelk/issues/197
[#199]: https://github.com/jupyrdf/ipyelk/issues/199
[#200]: https://github.com/jupyrdf/ipyelk/issues/200
[#201]: https://github.com/jupyrdf/ipyelk/issues/201
[#205]: https://github.com/jupyrdf/ipyelk/issues/205
[#214]: https://github.com/jupyrdf/ipyelk/issues/214
[#215]: https://github.com/jupyrdf/ipyelk/issues/215
[#216]: https://github.com/jupyrdf/ipyelk/issues/216
[#217]: https://github.com/jupyrdf/ipyelk/issues/217
[#218]: https://github.com/jupyrdf/ipyelk/issues/218
[#219]: https://github.com/jupyrdf/ipyelk/issues/219
[#227]: https://github.com/jupyrdf/ipyelk/issues/227
[#232]: https://github.com/jupyrdf/ipyelk/issues/232
[#237]: https://github.com/jupyrdf/ipyelk/issues/237
[#245]: https://github.com/jupyrdf/ipyelk/issues/245
[eclipse-sprotty/sprotty#573]: https://github.com/eclipse-sprotty/sprotty/issues/573
[ipykernel#1529]: https://github.com/ipython/ipykernel/pull/1529
[migration]: https://ipyelk.readthedocs.io/en/latest/migration.html
[migration-removed-names]:
  https://ipyelk.readthedocs.io/en/latest/migration.html#migration-removed-names

## `2.1.1`

### `@jupyrdf/jupyter-elk 2.1.1`

- restore license files

### `ipyelk 2.1.1`

- restore license files

## `2.1.0` (broken)

### `@jupyrdf/jupyter-elk 2.1.0`

- support JupyterLab 4.1-4.3

### `ipyelk 2.1.0`

- improve type hints

## `2.1.0a0`

### `@jupyrdf/jupyter-elk 2.1.0-alpha0`

- Update dependencies `elkjs 0.9.3`, `sprotty 1.3`, `jupyterlab 4.2`
- Add shim for `reflect-metadata` vs `fast-foundation`

### `ipyelk 2.1.0a0`

- Support `pydantic >=1,<3`

<!-- vale Vale.Terms = NO -->
<!-- released notes are kept as written -->

## `2.0.0`

### `@jupyrdf/jupyter-elk 2.0.0`

- Added control layer to allow jupyterlab widgets to exist on top of the diagram based
  on current node selection.
- Adding controllable render delay for jupyterlab widgets used in diagram nodes.
- Updated dependencies to `elkjs 0.8.2`.
- Fixed diagram bounding box issue affecting node visibility ([#94]).
- Improved test sizing that takes into account css properties ([#97])

### `ipyelk 2.0.0`

- Migrated to `ipywidgets >=8.0.1,<9`
- Added simple visualizer widget for the diagram pipe status.
- Fixed edge parent ownership affecting self edges ([#101])

[#94]: https://github.com/jupyrdf/ipyelk/issues/94
[#97]: https://github.com/jupyrdf/ipyelk/issues/97
[#101]: https://github.com/jupyrdf/ipyelk/issues/101

## `2.0.0a0`

### `@jupyrdf/jupyter-elk 2.0.0-alpha0`

- Label Schema fix ([#73])
- Element API overhaul ([#88])
  - Add `mypy` for type checking
  - Use `pydantic` for `Element` base models
- Overhaul top level interface ([#89])
  - Backporting Sprotty Duplicate ID ([#17])
  - Generalize the processing stages to use a common interface of Marks and simplify
    processing to composable pipes
  - Refactoring top level APIs and attempt and more streamlined `Diagram` creation

[#17]: https://github.com/jupyrdf/ipyelk/issues/17
[#87]: https://github.com/jupyrdf/ipyelk/pull/87
[#88]: https://github.com/jupyrdf/ipyelk/pull/88
[#89]: https://github.com/jupyrdf/ipyelk/issues/89

### `ipyelk 2.0.0a0`

## `1.0.1`

### `@jupyrdf/jupyter-elk 1.0.1`

- hides some browser console messages

### `ipyelk 1.0.1`

## `1.0.0`

### `@jupyrdf/jupyter-elk 1.0.0`

- updates for JupyterLab 3 ([#6])
  - uses `@lumino` components

### `ipyelk 1.0.0`

- supports (and depends on) JupyterLab 3 ([#6])
  - labextension is delivered as part of the `ipyelk` python package, no more
    `lab build`
  - `npm` tarballs will still be uploaded

[#6]: https://github.com/jupyrdf/ipyelk/issues/6

## `0.3.0`

### `@jupyrdf/jupyter-elk 0.3.0`

### `ipyelk 0.3.0`

- Custom shapes ([#60])
  - Ability to add custom SVG symbols and use as a reference for other elements
  - Custom node shapes
  - Custom connector end shapes for edges
  - Custom shapes for ports
  - Custom node label shapes
  - JupyterLab widgets rendering inside Node
  - Node compartments
  - Initial level of detail checks for labels
  - Rendering checks for nodes outside of view bounding box
- Initial [documentation] ([#64])

[documentation]: https://ipyelk.readthedocs.org
[#60]: https://github.com/jupyrdf/ipyelk/pull/60
[#64]: https://github.com/jupyrdf/ipyelk/pull/64

## `0.2.1`

### `@jupyrdf/jupyter-elk 0.2.1`

- fix `ElkTransformer` handling of custom properties ([#46])
- add `ElkTextSizer` passing through of custom CSS style when sizing labels ([#48])

### `ipyelk 0.2.1`

- update Elk schema to allow for properties (and c) on edge labels and port labels
  ([#48])
- Merge layout options if specified in a given node's data with default layout options
  ([#48])

[#46]: https://github.com/jupyrdf/ipyelk/pull/46
[#48]: https://github.com/jupyrdf/ipyelk/pull/48

## `0.2.0`

### `@jupyrdf/jupyter-elk 0.2.0`

- provides in-browser text measurement against ground-truth CSS ([#15])
- upgrades to `sprotty-elk 0.9.0` ([#15])
- adds basic browser testing with Robot Framework ([#21])
- adds SVG export with `ElkExporter` ([#27])
- handles multiple views of the same ELK model more robustly ([#36])

### `ipyelk 0.2.0`

- adds optional node label positioning with `NodeLabelPlacement` ([#15])
  - vertical/horizontal alignment
  - inside/outside the node
- improves evented updates of networkx to diagram with `ElkDiagram.connect(XElk)`
  ([#15])
- adds optional `ElkTextSizer` for interacting with browser text sizing ([#15])
- add layout options widgets to control various layout parameters ([#24])
- add support for multiline node labels, port labels, and edge labels ([#35])
  - adds possibility of passing CSS classes through to the final DOM elements

[#15]: https://github.com/jupyrdf/ipyelk/pull/15
[#21]: https://github.com/jupyrdf/ipyelk/pull/21
[#24]: https://github.com/jupyrdf/ipyelk/pull/24
[#27]: https://github.com/jupyrdf/ipyelk/pull/27
[#34]: https://github.com/jupyrdf/ipyelk/pull/34
[#36]: https://github.com/jupyrdf/ipyelk/pull/36

## `0.1.3`

### `@jupyrdf/jupyter-elk 0.1.3`

- includes all files using `npm publish`

### `ipyelk 0.1.3`

- updates some metadata for pypi

## `0.1.2`

### `ipyelk 0.1.2`

### `@jupyrdf/jupyter-elk 0.1.2` (broken)

- (failed) fix npm release process

## `0.1.1`

### `ipyelk 0.1.1`

- initial release

### `@jupyrdf/jupyter-elk 0.1.1` (broken)

- initial release
