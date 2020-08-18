# `ipyelk`

[Jupyter Widgets][widgets] for interactive graphs powered by the [Eclipse Layout Kernel
(ELK)][elk].

|            Demo             |        Build        |                          Docs                           |
| :-------------------------: | :-----------------: | :-----------------------------------------------------: |
| [![binder-badge][]][binder] | [![ci-badge][]][ci] | [CHANGELOG][] <br/> [CONTRIBUTING][] <br/> [examples][] |

![Interactive diagrams with elk.js, sprotty in JupyterLab][screenshot]

## Prerequisites

- `python >=3.7`
- `jupyterlab >=1,<2` _JupyterLab 2+ compatibility coming soon!_
- `nodejs >=10,<14`

## Install

`ipyelk` is distributed on [PyPI](https://pypi.org). `@jupyrdf/jupyter-elk` is
distributed on [npm](https://www.npmjs.com). Install them with:

```bash
pip install ipyelk
jupyter labextension install @jupyter-widgets/jupyterlab-manager @jupyrdf/jupyter-elk
```

> See [CONTRIBUTING][] for a development install.

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
[license]: https://github.com/jupyrdf/ipyelk/tree/master/LICENSE.md
[examples]: https://github.com/jupyrdf/ipyelk/tree/master/examples/00_Introduction.ipynb
[contributing]: https://github.com/jupyrdf/ipyelk/tree/master/CONTRIBUTING.md
[changelog]: https://github.com/jupyrdf/ipyelk/tree/master/CHANGELOG.md
[ci-badge]: https://github.com/jupyrdf/ipyelk/workflows/CI/badge.svg
[ci]: https://github.com/jupyrdf/ipyelk/actions?query=workflow%3ACI+branch%3Amaster
[binder-badge]: https://mybinder.org/badge_logo.svg
[binder]:
  https://mybinder.org/v2/gh/jupyrdf/ipyelk/master?urlpath=lab%2Ftree%2Fexamples%2F00_Introduction.ipynb
[elk-json]:
  https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
[elk]: https://github.com/kieler/elkjs
[jupyterlab]: https://github.com/jupyterlab/jupyterlab
[networkx]: https://networkx.github.io
[sprotty]: https://github.com/eclipse/sprotty
[widgets]: https://jupyter.org/widgets
[screenshot]:
  https://user-images.githubusercontent.com/7581399/90518838-40820300-e135-11ea-8e68-b19356794c78.png
