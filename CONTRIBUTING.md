# Contributing to `ipyelk`

## Install

- Get [Mambaforge](https://github.com/conda-forge/miniforge/releases/tag/4.9.2-5)
- Get [anaconda-project](https://anaconda-project.readthedocs.io) and
  [doit](https://pydoit.org)

```bash
mamba install anaconda-project=0.8.4 doit=0.32
```

## Get Started

```bash
git clone https://github.com/jupyrdf/ipyelk
cd ipyelk
doit list --all # see what you can do
doit            # this is _basically_ what happens on binder
doit lab        # start lab
```

## Branches

Presently, on GitHub:

- `master`: the `1.x` line, which distributes the lab extension inside the python
  distribution for JupyterLab `>3`
  - generates the `latest` tag on ReadTheDocs
  - PRs welcome for new features or bugfixes here, backport fixes to `0.3.x`
- `0.3.x`: the JupyterLab 1 (and, theoretically, 2) -compatible maintenance branch
  - generates the `0.3.x` tag on ReadTheDocs
  - PRs welcome for fixes here, forward-port to `master`

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

## Building Documentation

To build (and check the spelling and link health) of what _would_ go to
`ipyelk.readthedocs.org`, we:

- build with `sphinx` and `myst-nb`
- check spelling with `hunspell`
- check links with `pytest-check-links`

```bash
doit -n8 checkdocs
```

### Watch the Docs

`sphinx-autobuild` will try to watch docs sources for changes, re-build, and serve a
live-reloading website. A number of files (e.g. `_static`) won't often update correctly,
but will usually work when restarted.

```bash
doit watch_docs
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
