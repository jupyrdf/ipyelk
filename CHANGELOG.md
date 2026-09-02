# Changelog

## `2.1.2`

### Development

- Upgrade the pinned `pixi` from `0.34.0` to `0.67.0` (and `setup-pixi` to `v0.10.0`);
  relocking updates `libgfortran5` `13.2.0`→`14.2.0`, fixing a macOS arm64 dyld failure
  that broke `numpy`/`bqplot` in the example notebooks
- Only reinstall requirements in the `07_Simulation` example when `ipyelk` is missing,
  and add `tooltip`s to its control widgets

### `@jupyrdf/jupyter-elk 2.1.2`

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
- Add a `vitest` unit-test harness (F5)

### `ipyelk 2.1.2`

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
