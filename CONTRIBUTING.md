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

## Important Paths

| Path                           | Purpose                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------- |
| `anaconda-project.yml`         | the current environment and task automation tool, may be replaced in the future |
| `anaconda-project-lock.yml`    | the frozen environments                                                         |
| `ipyelk/`                      | the Python source for `ipyelk`                                                  |
| `ipyelk/schema/elkschema.json` | the JSON schema derived from the TypeScript source                              |
| `src/`                         | the TypeScript source for `@jupyrdf/jupyter-elk`                                |

- Most python-related commands are run with `anaconda-project run`
- Most typescript-related commands are run with
  `anaconda-project run jlpm <script in package.json>`

## Live Development

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

- Run:

```bash
anaconda-project run watch
```

- Open a tab with the provided URL in your standards-compliant browser of choice
- After making changes, reload your browser

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
anaconda-project run lint
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
