# Contributing to `ipyelk`

## Install

- Get [Miniforge](https://github.com/conda-forge/miniforge)
- Get [pixi](https://pixi.sh)

```bash
mamba install pixi
```

## Get Started

```bash
git clone https://github.com/jupyrdf/ipyelk
cd ipyelk
pixi task list      # that's a lot
pixi run release    # this is _basically_ what happens on CI
pixi run lab        # start lab
```

## Branches

Presently, on GitHub:

- `master`: the `2.x` line, which distributes the lab extension inside the python
  distribution for JupyterLab `>=4.2`
  - generates the `latest` tag on ReadTheDocs

## Important Paths

| Path                               | Purpose                                              |
| ---------------------------------- | ---------------------------------------------------- |
| `atest/`                           | Robot Framework source for acceptance tests          |
| `pixi.toml`                        | task automation tool                                 |
| `pixi.lock`                        | pinned build/test/docs environments                  |
| `js/`                              | TypeScript source for `@jupyrdf/jupyter-elk`         |
| `package.json/`                    | `npm` package description for `@jupyrdf/jupyter-elk` |
| `pyproject.toml`                   | package description for `ipyelk`                     |
| `src/`                             | Python source for `ipyelk`                           |
| `src/ipyelk/schema/elkschema.json` | JSON schema derived from the TypeScript source       |
| `yarn.lock`                        | frozen `npm` dependencies                            |
| `docs/`                            | documentation                                        |
| `examples/`                        | examples, used in demo and test                      |
| `lite/`                            | JupyterLite demo configuration                       |

- Run `pixi run dev-ext` to get ready to develop
- Most commands are run with `pixi run release` (this is what CI does)

## Live Development

You can watch the source directory and run JupyterLab in watch mode to watch for changes
in the extension's source and automatically rebuild the extension and application.

- Run:

```bash
pixi run watch
```

- Open a tab with the provided URL in a standards-compliant browser of choice
- After making changes, wait for `webpack` terminal output, then reload the browser
- If you add a new file, probably will have to restart the whole thing

### Logging

In the browser, `jupyter-elk` should only emit `console.warn` (or higher) messages if
there's actually a problem.

For more verbose output, add `ELK_DEBUG` anywhere in a new browser URL, e.g.

```bash
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
pixi run fix
pixi run lint
```

- Ensure the `examples/` work. These will be tested in CI with:
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
ATEST_ARGS="--exclude NOTsome:tag" pixi run atest-robot
```

## Building Documentation

To build (and check the spelling and link health) of what _would_ go to
`ipyelk.readthedocs.org`, we:

- build with `sphinx` and `myst-nb`
- check spelling with `vale`
- check links with `pytest-check-links`

```bash
pixi run check
```

### Watch the Docs

`sphinx-autobuild` will try to watch docs sources for changes, re-build, and serve a
live-reloading website. A number of files (e.g. `_static`) won't often update correctly,
but will usually work when restarted.

```bash
pixi run watch-docs
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
npm login
npm publish
npm logout
twine upload where-you-expanded-the-archive/ipyelk-*
```

## Updating Dependencies

### Python Dependencies

- Edit the `feature.*.dependencies` section of `pixi.toml`
- Run:

```bash
pixi run fix
```

- Commit the changes to `pixi.toml` and `pixi.lock`

### Browser Dependencies

- Edit the appropriate section of `./package.json`.
- Run:

```bash
pixi run setup-js || pixi run setup-js || pixi run setup-js
pixi run fix
```

- Commit the changes to `./package.json` and the `./yarn.lock`.
