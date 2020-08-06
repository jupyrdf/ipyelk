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

## Uninstall

```bash
pip uninstall ipyelk
jupyter labextension uninstall @jupyrdf/jupyter-elk
```

[widgets]: https://jupyter.org/widgets
[elk]: https://github.com/kieler/elkjs
[jupyterlab]: https://github.com/jupyterlab/jupyterlab
