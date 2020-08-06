# Contributing to `ipyelk`

## Install

- Get [Miniconda3](https://docs.conda.io/en/latest/miniconda.html)
- Get [anaconda-project](https://anaconda-project.readthedocs.io)

## Get Started

```bash
git clone https://github.com/jupyrdf/ipyelk
cd ipyelk
anaconda-project run setup    # this is what happens on binder
anaconda-project run dev      # setup the local labextension
anaconda-project run lab      # start lab
```

## Live Development

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

- Run:

```bash
anaconda-project run jlpm watch  # Watch the source directory in one terminal tab
anaconda-project run lab --watch  # Watch lab in another terminal tab
```

- Open a tab with the provided URL in your standards-compliant browser of choice

## Quality Assurance

- Run:

```bash
anaconda-project run lint
```

- Ensure the [examples](./examples) work.
- If you add new features:
  - Add a new, minimal demonstration notebook to the examples.
  - Add appropriate links to your new example.

## Releasing

- Run:

```bash
anaconda-project run dist
```

- See the files in `./dist`.

> - TBD: Do something with the files.

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

- Commit the changes to the package file and the [yarn lock file](./yarn.lock).
