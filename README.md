
# elk-widget

[![Build Status](https://travis-ci.org/gtri/elk-widget.svg?branch=master)](https://travis-ci.org/gtri/elk)
[![codecov](https://codecov.io/gh/gtri/elk-widget/branch/master/graph/badge.svg)](https://codecov.io/gh/gtri/elk-widget)


ELK widget for Jupyter

## Installation

A typical installation requires the following commands to be run:

```bash
pip install elk
jupyter nbextension enable --py [--sys-prefix|--user|--system] elk
```

Or, if you use jupyterlab:

```bash
pip install elk
jupyter labextension install @jupyter-widgets/jupyterlab-manager
```
