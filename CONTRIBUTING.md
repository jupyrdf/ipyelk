# Contributing to `elk-widget`

## Install

- Get [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Get [anaconda-project](https://anaconda-project.readthedocs.io)

## Get Started

```bash
# Clone the repo to your local environment
anaconda-project run setup
anaconda-project run lab
```

## Live Development

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

```bash
# Watch the source directory in another terminal tab
anaconda-project run jlpm watch
# Run jupyterlab in watch mode in one terminal tab
anaconda-project run lab --watch
```

## Quality Assurance

- keep the linters/formatters happy

```bash
anaconda-project run lint
```

- Ensure the [examples](./examples) work.
- If you add new features:
  - Add a new, minimal demonstration notebook to the examples.
  - Add appropriate links to your new example.

## Updating Dependencies

### Python Dependencies

- Edit the `env_specs` section of [project file](./anaconda-project.yml).
- Run:

```bash
anaconda-project update
```

- Commit the changes to the project file and the
  [project lock file](./anaconda-project-lock.yml).

### Browser Dependencies

- Edit the appropriate section of the [package file](./package.json).
- Run:

```bash
anaconda-project run jlpm
```

- Commit the changes to the package file and the [browser lock file](./yarn.lock).
