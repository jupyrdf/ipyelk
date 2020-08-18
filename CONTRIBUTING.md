# Contributing to `ipyelk`

## Install

- Get [Miniconda3](https://docs.conda.io/en/latest/miniconda.html)
- Get [anaconda-project](https://anaconda-project.readthedocs.io)
- Get [doit](https://pydoit.org)

```bash
conda install anaconda-project=0.8.4 doit=0.32
```

## Get Started

```bash
git clone https://github.com/jupyrdf/ipyelk
cd ipyelk
doit       # this is _basically_ what happens on binder
doit lab   # start lab
```

## Important Paths

| Path                                  | Purpose                                              |
| ------------------------------------- | ---------------------------------------------------- |
| `dodo.py`                             | task automation tool                                 |
| `anaconda-project.yml`                | environment templates and some task definitions      |
| `anaconda-project-lock.yml`           | frozen environments                                  |
| `setup.py` / `setup.cfg`              | package description for `ipyelk`                     |
| `py_src/`                             | Python source for `ipyelk`                           |
| `py_src/ipyelk/schema/elkschema.json` | JSON schema derived from the TypeScript source       |
| `package.json/`                       | `npm` package description for `@jupyrdf/jupyter-elk` |
| `yarn.lock`                           | frozen `npm` dependencies                            |
| `src/`                                | TypeScript source for `@jupyrdf/jupyter-elk`         |

- Most commands are run with `doit`
- Most typescript-related commands are run with
  `anaconda-project run jlpm <script in package.json>`

## Live Development

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

- Run:

```bash
doit watch
```

- Open a tab with the provided URL in a standards-compliant browser of choice
- After making changes, wait for `webpack` terminal output, then reload the browser
- If you add a new file, probably will have to restart the whole thing

## Quality Assurance

- Run:

```bash
doit lint
```

- Ensure the [examples](./examples) work.
- If you add new features:
  - Add a new, minimal demonstration notebook to the examples.
  - Add appropriate links to your new example.

## Releasing

- After merging to `master`, download the ipyelk dist artifacts
- Inspect the files in `./dist`.
- Check out master
- Tag appropriately

```bash
git push upstream --tags
```

- Ensure you have credentials for `pypi` and `npmjs`

```bash
cd where-you-expanded-the-archive
anaconda-project run twine upload ipyelk-*
anaconda-project run jlpm publish jupyrdf-jupyter-elk-*.tgz
```

## Updating Dependencies

### Python Dependencies

- Edit the `env_specs` section of [project file](./anaconda-project.yml).
- Run:

```bash
anaconda-project update
doit lint
```

- Commit the changes to the project file and the
  [project lock file](./anaconda-project-lock.yml).

### Browser Dependencies

- Edit the appropriate section of the [package file](./package.json).
- Run:

```bash
doit setup:js
doit lint
```

- Commit the changes to the package file and the [yarn lock file](./yarn.lock).
