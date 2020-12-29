# Changelog

## ipyelk 0.3.0

- support JupyterLab 3 ([#6][])
  - `@jupyrdf/jupyter-elk` is now bundled in the `pip`/`conda` package, and no
    `jupyter lab build` is required

## @jupyrdf/jupyter-elk 0.3.0

- uses newer `@lumino` and `@jupyter-widgets` packages
- packages will continue to be released on npmjs.org, and _might_ even install from the
  extension manager, but this is _no longer be tested_

[#6]: https://github.com/jupyrdf/ipyelk/issues/6

## @jupyrdf/jupyter-elk 0.3.0

---

## @jupyrdf/jupyter-elk 0.2.1

- fix `ElkTransformer` handling of custom properties ([#46][])
- add `ElkTextSizer` passing through of custom css style when sizing labels ([#48][])

## ipyelk 0.2.1

- update Elk schema to allow for properties (and c) on edge labels and port labels
  ([#48][])
- Merge layout options if specified in a given node's data with default layout options
  ([#48][])

[#46]: https://github.com/jupyrdf/ipyelk/pull/46
[#48]: https://github.com/jupyrdf/ipyelk/pull/48

---

## @jupyrdf/jupyter-elk 0.2.0

- provides in-browser text measurement against ground-truth CSS ([#15][])
- upgrades to `sprotty-elk 0.9.0` ([#15][])
- adds basic browser testing with Robot Framework ([#21][])
- adds SVG export with `ElkExporter` ([#27][])
- handles multiple views of the same ELK model more robustly ([#36][])

## ipyelk 0.2.0

- adds optional node label positioning with `NodeLabelPlacement` ([#15][])
  - vertical/horizontal alignment
  - inside/outside the node
- improves evented updates of networkx to diagram with `ElkDiagram.connect(XElk)`
  ([#15][])
- adds optional `ElkTextSizer` for interacting with browser text sizing ([#15][])
- add layout options widgets to control various layout parameters ([#24][])
- add support for multiline node labels, port labels, and edge labels ([#35][])
  - adds possibility of passing css classes through to the final DOM elements

[#15]: https://github.com/jupyrdf/ipyelk/pull/15
[#21]: https://github.com/jupyrdf/ipyelk/pull/21
[#24]: https://github.com/jupyrdf/ipyelk/pull/24
[#27]: https://github.com/jupyrdf/ipyelk/pull/27
[#34]: https://github.com/jupyrdf/ipyelk/pull/34
[#36]: https://github.com/jupyrdf/ipyelk/pull/36

---

## @jupyrdf/jupyter-elk 0.1.3

- includes all files using `npm publish`

## ipyelk 0.1.3

- updates some metadata for pypi

---

## ipyelk 0.1.2

## @jupyrdf/jupyter-elk 0.1.2 (broken)

- (failed) fix npm release process

---

## ipyelk 0.1.1

- initial release

## @jupyrdf/jupyter-elk 0.1.1 (broken)

- initial release
