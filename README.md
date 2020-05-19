# elk-widget

[ELK](https://github.com/kieler/elkjs) widget for Jupyter

See the [example notebooks](./examples/00_Introduction.ipynb)

## Install

```bash
jupyter labextension install @jupyter-widgets/jupyterlab-manager elk-widget
```

### Uninstall

```bash
jupyter labextension uninstall elk-widget
```

## Contributing

### Install

- Get [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Get [anaconda-project](https://anaconda-project.readthedocs.io)

```bash
# Clone the repo to your local environment
anaconda-project run setup
anaconda-project run lab:ext
```

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

```bash
# Watch the source directory in another terminal tab
anaconda-project run jlpm watch
# Run jupyterlab in watch mode in one terminal tab
anaconda-project run lab --watch
```
