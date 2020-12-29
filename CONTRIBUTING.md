# Contributing to `ipyelk`

## Install

- Get [Miniforge](https://github.com/conda-forge/miniforge)
- Get [anaconda-project](https://anaconda-project.readthedocs.io)
- Get [doit](https://pydoit.org)

```bash
conda install anaconda-project=0.8.4 doit=0.32
```

To have an environment _similar_ to what's on CI:

```bash
CONDA_EXE=$(which mamba) CONDARC=.github/.condarc conda env update --file .github/environment.yml
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
| `atest/`                              | Robot Framework source for acceptance tests          |

- Run `doit` to get ready to develop
- Most commands are run with `doit all` (this is what CI does)
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

### Logging

In the browser, `jupyter-elk` should only emit `console.warn` (or higher) messages if
there's actually a problem.

For more verbose output, add `ELK_DEBUG` anywhere in a new browser URL, e.g.

```http
http://localhost:8888/lab#ELK_DEBUG
```

> Note: if a message will be helpful for debugging, make sure to `import` and guard
> `console.*` or higher with `ELK_DEBUG &&`

On the python side, each `Widget` has `.log.debug` which is preferable to `print`
statements. The log level can be increased for a running kernel through the JupyterLab's
_Log Console_, opened with the _Show Log Console_ command.

## Quality Assurance

- Run:

```bash
doit lint
```

- Ensure the [examples](./examples) work. These will be tested in CI with:
  - `nbconvert --execute`
  - in JupyterLab by Robot Framework with _Restart Kernel and Run All Cells_
- If you add new features:
  - Add a new, minimal demonstration notebook to the examples.
    - Treat each feature as a function which can be reused for other examples, with:
      - the example in a humane name, e.g. `a_basic_elk_example`
      - some suitable defaults and knobs to twiddle
  - Add appropriate links to your new example.
  - Add appropriate Robot Framework tests

### Limiting Testing

To run just _some_ acceptance tests, add something like:

```robotframework
*** Test Cases ***
Some Test
  [Tags]  some:tag
  ...
```

Then run:

```bash
ATEST_ARGS="--exclude NOTsome:tag" doit test:atest
```

## Releasing

- After merging to `master`, download the ipyelk dist artifacts
- Inspect the files in `./dist`.
- Check out master
- Tag appropriately

```bash
git push upstream --tags
```

- Ensure you have credentials for `pypi` and `npmjs`
  - `npmjs` requires you have set up two-factor authentication (2FA)... this is
    _strongly recommended_ for `pypi`
  - do _not_ use `jlpm publish` or `yarn publish`, as this appears to drop files from
    the distribution

```bash
anaconda-project run npm login
anaconda-project run npm publish
anaconda-project run npm logout
anaconda-project run twine upload where-you-expanded-the-archive/ipyelk-*
```

## Updating Dependencies

### Python Dependencies

- Edit the `env_specs` section of [project file](./anaconda-project.yml).
- Run:

```bash
python scripts/lock.py
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
