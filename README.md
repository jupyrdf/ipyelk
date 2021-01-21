# `ipyelk`

[Jupyter Widgets][widgets] for interactive graphs powered by the [Eclipse Layout Kernel
(ELK)][elk].

|                                        Install                                        |            Demo             |        Build        |                                         Docs                                         |
| :-----------------------------------------------------------------------------------: | :-------------------------: | :-----------------: | :----------------------------------------------------------------------------------: |
| [![npm-badge]][npm] <br/> [![pypi-badge][]][pypi] <br/> [![conda-badge]][conda-forge] | [![binder-badge][]][binder] | [![ci-badge][]][ci] | [![][docs-badge]][docs] <br/> [Examples][] <br/>[CHANGELOG][] <br/> [CONTRIBUTING][] |

## Screenshots

| what can you do...                                     | ... with `ipyelk`              |
| ------------------------------------------------------ | ------------------------------ |
| automatically lay out complex, nested data as diagrams | ![][screenshot]                |
| interactive activity/flow-chart diagrams               | ![][screenshot-activities]     |
| collapsible blocks                                     | ![][screenshot-activity-block] |
| visual simulations                                     | ![][screenshot-1-bit]          |

## Prerequisites

- `python >=3.7`
- `jupyterlab >=1,<2` _JupyterLab 2+ compatibility coming soon!_
- `nodejs >=10,<14`

## Install

`ipyelk` is distributed on [conda-forge][] and [PyPI][].

### `ipyelk` with `conda` (recommended)

`conda` can also install `nodejs`.

```bash
conda install -c conda-forge ipyelk jupyterlab=1 nodejs
```

### `ipyelk` with `pip`

install `nodejs` with a [package manager][package-manager]

```bash
pip install ipyelk jupyterlab=1
```

### `@jupyrdf/jupyter-elk` with `jupyter labextension install`

`@jupyrdf/jupyter-elk` is distributed on [npm][], and relies on
`@jupyter-widgets/jupyterlab-manager`.

```bash
jupyter labextension install @jupyter-widgets/jupyterlab-manager @jupyrdf/jupyter-elk
```

### Developing

See [CONTRIBUTING][] for a development install.

## How it works

In your kernel, `ipyelk`:

- build [ELK JSON][elk-json]
  - optionally, use [networkx][]

In the browser, `@jupyrdf/jupyter-elk`:

- [ELK][] lays out the diagram in a WebWorker
- [sprotty][] draws the diagram as SVG
- interaction information (like selection and hovering) are passed back to the browser

## Uninstall

```bash
pip uninstall ipyelk
jupyter labextension uninstall @jupyrdf/jupyter-elk
```

## Open Source

This work is licensed under the [BSD-3-Clause License][license]. It contains pieces
derived from [other works][copyright].

[copyright]: https://github.com/jupyrdf/ipyelk/tree/master/COPYRIGHT.md
[license]: https://github.com/jupyrdf/ipyelk/tree/master/LICENSE.txt
[docs]: https://ipyelk.readthedocs.org
[docs-badge]: https://readthedocs.org/projects/ipyelk/badge/?version=latest
[examples]: https://github.com/jupyrdf/ipyelk/tree/master/examples/_index.ipynb
[contributing]: https://github.com/jupyrdf/ipyelk/tree/master/CONTRIBUTING.md
[changelog]: https://github.com/jupyrdf/ipyelk/tree/master/CHANGELOG.md
[ci-badge]: https://github.com/jupyrdf/ipyelk/workflows/CI/badge.svg
[ci]: https://github.com/jupyrdf/ipyelk/actions?query=workflow%3ACI+branch%3Amaster
[binder-badge]: https://mybinder.org/badge_logo.svg
[binder]:
  https://mybinder.org/v2/gh/jupyrdf/ipyelk/master?urlpath=lab%2Ftree%2Fexamples%2F_index.ipynb
[elk-json]:
  https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
[elk]: https://github.com/kieler/elkjs
[jupyterlab]: https://github.com/jupyterlab/jupyterlab
[networkx]: https://networkx.github.io
[sprotty]: https://github.com/eclipse/sprotty
[widgets]: https://jupyter.org/widgets
[screenshot]:
  https://user-images.githubusercontent.com/7581399/90518838-40820300-e135-11ea-8e68-b19356794c78.png
[screenshot-activities]:
  https://user-images.githubusercontent.com/7581399/105381388-f36ef500-5bdc-11eb-8208-d227951b806e.gif
[screenshot-activity-block]:
  https://user-images.githubusercontent.com/7581399/105381390-f4a02200-5bdc-11eb-808e-844ee17cad8f.gif
[screenshot-1-bit]:
  https://user-images.githubusercontent.com/7581399/105381389-f4a02200-5bdc-11eb-975d-e4a09c4f0c96.gif
[npm-badge]: https://img.shields.io/npm/v/@jupyrdf/jupyter-elk
[npm]: https://www.npmjs.com/package/@jupyrdf/jupyter-elk
[pypi]: https://pypi.org/project/ipyelk
[pypi-badge]: https://img.shields.io/pypi/v/ipyelk
[conda-badge]: https://img.shields.io/conda/vn/conda-forge/ipyelk
[conda-forge]: https://anaconda.org/conda-forge/ipyelk/
[package-manager]: https://nodejs.org/en/download/package-manager
