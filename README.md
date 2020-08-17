# `ipyelk`

[Jupyter Widgets][widgets] for interactive graphs powered by the [Eclipse Layout Kernel
(ELK)][elk].

|            Demo             |        Build        |                          Docs                           |
| :-------------------------: | :-----------------: | :-----------------------------------------------------: |
| [![binder-badge][]][binder] | [![ci-badge][]][ci] | [CHANGELOG][] <br/> [CONTRIBUTING][] <br/> [examples][] |

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
