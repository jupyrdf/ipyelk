# `ipyelk`

[Jupyter Widgets][widgets] for interactive graphs powered by the [Eclipse Layout Kernel
(ELK)][elk].

|                                        Install                                        |        Build        |                                         Docs                                         |
| :-----------------------------------------------------------------------------------: | :-----------------: | :----------------------------------------------------------------------------------: |
| [![npm-badge]][npm] <br/> [![pypi-badge][]][pypi] <br/> [![conda-badge]][conda-forge] | [![ci-badge][]][ci] | [![][docs-badge]][docs] <br/> [Examples][] <br/>[CHANGELOG][] <br/> [CONTRIBUTING][] |

## Screenshots

| what can you do...                                     | ... with `ipyelk`                                                                      |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| automatically lay out complex, nested data as diagrams | ![a screenshot of a complex graph][screenshot]                                         |
| interactive activity/flow-chart diagrams               | ![a screencast of a flowchart with collapsible regions][screenshot-activities]         |
| collapsible blocks                                     | ![a screencast of a class diagram with collapsible regions][screenshot-activity-block] |
| visual simulations                                     | ![a screencast of an interactive logic gate simulation][screenshot-1-bit]              |
| embed other widgets in diagrams                        | ![a screencast of displaying bar and scatter plots in a flowchart][screenshot-overlay] |
| interact with dynamic systems                          | ![a screencast of a predator/prey system with plots over time][screenshot-deer-wolves] |

## Prerequisites

- `python >=3.9`

### JupyterLab compatibility

| `jupyterlab` | `ipyelk`   | special concerns                                                                                                          |
| ------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| `==1.*`      | `>1`       | needs `nodejs >10`<br/>`jupyter labextension install @jupyrdf/jupyter-elk`<br/>backports, etc. land on the `0.3.x` branch |
| `==2.*`      | `>1`       | _untested_                                                                                                                |
| `==3.*`      | `>=1,<2.1` |
| `>=4.1,<5`   | `>=2.1`    |

## Install

`ipyelk` is distributed on [conda-forge][] and [PyPI][].

### `ipyelk` with `conda` (recommended)

```bash
conda install -c conda-forge ipyelk "jupyterlab=4.*"
# or
mamba install -c conda-forge ipyelk "jupyterlab=4.*"
```

### `ipyelk` with `pip`

```bash
pip install ipyelk "jupyterlab=4.*"
```

### Developing

See [CONTRIBUTING][] for a development install.

## How it works

In your kernel, `ipyelk`:

- build [ELK JSON][elk-json]
  - optionally, use [networkx][]

In your `jupyter_server`:

- serve the `@jupyrdf/jupyter-elk` assets as a
  [federated module](https://jupyterlab.readthedocs.io/en/latest/extension/extension_dev.html#prebuilt-extensions)

In the browser, `@jupyrdf/jupyter-elk`:

- [ELK][] lays out the diagram in a WebWorker
- [sprotty][] draws the diagram as SVG
- interaction information (like selection and hovering) are passed back to the browser

## Uninstall

```bash
pip uninstall ipyelk
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
[screenshot-overlay]:
  https://github.com/user-attachments/assets/7cb454ab-d25b-4184-9632-018fa859cc25
[screenshot-deer-wolves]:
  https://github.com/user-attachments/assets/db2dd114-3104-4b8d-9f99-f7a9127214d8
[npm-badge]: https://img.shields.io/npm/v/@jupyrdf/jupyter-elk
[npm]: https://www.npmjs.com/package/@jupyrdf/jupyter-elk
[pypi]: https://pypi.org/project/ipyelk
[pypi-badge]: https://img.shields.io/pypi/v/ipyelk
[conda-badge]: https://img.shields.io/conda/vn/conda-forge/ipyelk
[conda-forge]: https://anaconda.org/conda-forge/ipyelk/
[package-manager]: https://nodejs.org/en/download/package-manager
