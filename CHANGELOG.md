# Changelog

## `3.0.0` (unreleased)

### Breaking changes

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
- `Hover.ids` is replaced by `Hover.hovered_id: str | None` (default `None`). There is
  no alias: code that reads or observes `ids` on the hover tool must switch to
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
  `Painter.cssClasses`, `Painter.marks`, `Painter.name`, and assigning `Tool.on_done`
  raise `ipyelk.exceptions.DeprecatedAPIError` on read, assignment, and as constructor
  keywords, with the reason and the replacement in the message (mechanism:
  `ipyelk.exceptions.RemovedAPI` / `check_removed`; a module-level `__getattr__` for the
  removed class names). Importing the misspelled `ipyelk.tools.contol_overlay` module
  raises the same error naming the new path; it re-exports nothing.

### Migration

```python
# 2.x: a Tool subclass that hand-rolled the merge to avoid clobbering the flow
inlet.flow = tuple(dict.fromkeys((*inlet.flow, *self.reports)))
# 3.0: the base class does this; drop the hand-rolled merge or call
self.record_reports()

# 2.x                                   # 3.0
button.on_click(tool.handler)           button.on_click(tool.trigger)
await tool.handler()                    await tool.trigger()
FitTool(handler=lambda: view.fit())     FitTool(on_click=lambda tool: view.fit())
tool.on_run(callback)                   tool.on_start(callback)   # when work starts
                                        tool.on_done(callback)    # success only
tool.on_done = callback                 tool.on_done(callback)    # + remove=True
toolbar.on_close = lambda: ...          toolbar.on_close = lambda toolbar: ...
tool.disable = True                     tool.disabled = True   # now actually disables
# a Tool subclass that did its work synchronously and refreshed by hand:
inlet.flow = (...); self.on_done()      self.trigger()  # run() may be a no-op
```

```python
# 2.x
hover.ids  # last hovered id, never reset
# 3.0
hover.hovered_id  # id under the pointer, or None
hover.hovered_id = "n1"  # highlight from the kernel
hover.hovered_id = None  # clear the highlight
```

```python
# 2.x: every viewer allocated an overlay, rendered even when empty
view.control_overlay.children = [button]
# 3.0: opt in first
from ipyelk.tools import ControlOverlay  # was ipyelk.tools.contol_overlay

view.control_overlay = ControlOverlay()
view.control_overlay.children = [button]
view.control_overlay.children = []  # renders nothing
```

```python
# 2.x: placeholders nothing ever wrote
view.zoom.zoom, view.pan.origin, view.viewed
# 3.0: the browser's latest report (None until a view reports), one snapshot
view.viewport.zoom, view.viewport.origin, view.viewport.viewed_ids
view.viewport.view_id  # which view reported
view.viewport.observe(callback, "origin")  # every field is already updated
# move a view (a command, not state)
view.set_viewport(origin=(0, 0), zoom=1.5)  # every view, animated
view.set_viewport(zoom=2, animate=False, view_id=view.viewport.view_id)
```

```python
# 2.x: Painter(cssClasses=..., marks=..., name=...) painted nothing
# 3.0: view-only classes per id, applied in every view, never in the model
view.painter.paint(["n1", "n2"], "highlight")  # or elements
view.painter.unpaint("n1", "highlight")  # drop a class; unpaint("n1") drops the id
view.painter.clear()
view.painter.styles  # {"n2": ("highlight",)}
```

The removed names (`handler`, `on_run`, `disable`, `Hover.ids`, assigning `on_done`, the
`contol_overlay` module, `Viewer.zoom`/`pan`/`viewed`, `ipyelk.tools.Zoom`/`Pan`,
`Painter.cssClasses`/`marks`/`name`) raise `DeprecatedAPIError` throughout 3.x with the
replacement in the message.

### `@jupyrdf/jupyter-elk 3.0.0`

- Upgrade ELK.js from `0.9.3` to `0.12.0` ([#140]). `ElkEdge` gains an optional
  `container` field in the generated schema.
- Upgrade `sprotty` and `sprotty-protocol` from `1.3.0` to `1.4.0`, which requires
  `inversify ^6.1.3` (pinned to `6.2.2`) and `reflect-metadata ^0.2.2`. The `inversify`
  shared module declares its `version` statically: its `lib/esm` entry ships a
  version-less `package.json`, so webpack module federation would otherwise register it
  as `0` and warn on every page load; a unit test keeps the static version equal to the
  dependency pin.
- Drop the unused `sprotty-elk` dependency: nothing in `js/` ever imported it, `sprotty`
  and `sprotty-protocol` do not depend on it, and the built extension has no reference
  to it. Its `elkjs ^0.8.2` range was the only thing that conflicted with ELK.js
  `0.12.0`, so the `resolutions.elkjs` override goes with it ([#140]).
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

[#140]: https://github.com/jupyrdf/ipyelk/issues/140
[#155]: https://github.com/jupyrdf/ipyelk/issues/155
[#156]: https://github.com/jupyrdf/ipyelk/issues/156

## `2.1.2`

### Development

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

### `@jupyrdf/jupyter-elk 2.1.2`

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

### `ipyelk 2.1.2`

- Allow diagram construction without a running event loop. `Pipe.schedule_run()` and
  `Diagram.refresh()` return `None` when they cannot schedule a task.
- Add optional `LabelProperties.tooltip` and `LabelProperties.separator` fields.
- Re-send widget state after a browser reports missing state, with throttling.
- Echo terminal progress state twice, cancelling pending echoes on updates and close.
- Fix `IDReport.message()` printing literal `{eid}`/`{el}` placeholders (F1)
- Fix `Pipeline.check()` / `get_progress_value()` crashing on an empty pipeline (F2)
- Give each `Tool` its own `on_run` callback dispatcher (was shared across all tools)
  (F3)
- Surface pipe/diagram exceptions via an `on_error` callback instead of silently
  dropping them in the asyncio done-callback (F4)
- Add a configurable `timeout` and a browser→kernel error channel to
  `ElkJS`/`BrowserTextSizer` so a failed or silent browser layout no longer hangs the
  diagram (F6)
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
