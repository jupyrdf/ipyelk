# `ipyelk`

[Jupyter Widgets][widgets] for interactive graphs powered by the [Eclipse Layout Kernel
(ELK)][elk]

> For more, see the [example notebooks](./examples/00_Introduction.ipynb)

## Install

> This extension is not currently published. See [CONTRIBUTING](./CONTRIBUTING.md) for a
> development install.

```bash
pip install ipyelk
jupyter labextension install @jupyter-widgets/jupyterlab-manager @jupyrdf/jupyter-elk
```

## How it works

In your kernel:

- build [ELK JSON][elk-json]
  - optionally, use [networkx][]

In the browser:

- [ELK][] lays out the diagram in a WebWorker
- [sprotty][] draws the diagram as SVG
- interaction information (like selection and hovering) are passed back to the browser

## Uninstall

```bash
pip uninstall ipyelk
jupyter labextension uninstall @jupyrdf/jupyter-elk
```

[widgets]: https://jupyter.org/widgets
[elk]: https://github.com/kieler/elkjs
[jupyterlab]: https://github.com/jupyterlab/jupyterlab
[elk-json]:
  https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html
[sprotty]: https://github.com/eclipse/sprotty
[networkx]: https://networkx.github.io
