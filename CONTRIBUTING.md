# Contributing to `ipyelk`

## Install

- Get [Miniforge](https://github.com/conda-forge/miniforge)
- Get [pixi](https://pixi.sh)

```bash
mamba install "pixi==0.67.0"
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
pixi run watch-js
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
pixi run lint-mypy  # run only the Python type checker
pixi run test
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
    - These will be picked up by `itest`
  - Potentially add some unit `./tests`
  - Add appropriate Robot Framework in `./atest`
- Ensure coverage doesn't degrade from the `ALL_PY_COV_FAIL_UNDER` baseline in
  `.github/workflows/ci.yml`

### Structural Lint Rules

`pixi run lint-ast-grep` runs [`ast-grep`](https://ast-grep.github.io) with the rules in
`scripts/ast-grep/rules/`, after checking them against their cases in
`scripts/ast-grep/rule-tests/`. These catch hazards specific to this code base that
`ruff`, `mypy` and `tsc` do not.

- Add a rule as `scripts/ast-grep/rules/<id>.yml` with a `message` and a short `note`
  saying why, and `scripts/ast-grep/rule-tests/<id>-test.yml` with `valid` and `invalid`
  cases
- Try a pattern with `pixi run -e lint ast-grep run -l py -p '<pattern>' src`
- Run only the rule tests with `pixi run -e lint ast-grep test --skip-snapshot-tests`
- Suppress an intended finding with the rule id, and the reason on the line above; a
  bare `ast-grep-ignore` (checked by `scripts/check_suppressions.py`) or one that no
  longer matches anything fails the lint:

```ts
// a foreignObject shape renders its `use` markup by design
// ast-grep-ignore: ts-no-html-injection
let contents = html('div', { props: { innerHTML: node?.properties?.shape?.use } });
```

`ast-grep` cannot parse notebooks, so `examples/*.ipynb` are not scanned. Known gaps,
accepted as unlikely: `window['eval']`, `Reflect.apply(eval, ...)` and `const e = eval`;
`el['insertAdjacentHTML']`, `contentDocument.write`, `srcdoc` and
`DOMParser.parseFromString`; `console.log.call`/`.apply`; and an `Instance` nested in
`T.Tuple(...)` next to a JSON one.

### Prose

[Vale](https://vale.sh) lints the prose in the root `*.md` files, `docs/`, docstrings
and comments in `src/`, `tests/` and `scripts/`, and notebook markdown cells, in US
English, with the `proselint` and `write-good` styles. Any warning or error fails
`pixi run lint`. To run it alone:

```bash
pixi run lint-vale
```

Findings in notebooks point at `build/nblint/examples/<notebook>/cell-<n>.md`, the
markdown of the _n_-th cell.

- Fix real typos. Vale doesn't spell-check hyphenated words (e.g. `re-serialised`
  passes), so check those by eye.
- Add a project term (a name, an API word) to
  `scripts/vale/config/vocabularies/IPyElk/accept.txt`, one per line. Entries are
  regular expressions, and `Vale.Terms` also enforces their case: write a lowercase word
  as `[Ww]ord` so it may start a sentence, or prefix `(?i)` to accept any case.
- In markdown, turn a rule off for one passage, with the reason:

```markdown
<!-- vale proselint.Very = NO -->
<!-- quoting the upstream docs verbatim -->

It is very fast.

<!-- vale proselint.Very = YES -->
```

- In Python, Vale has no inline switch, and it can't skip RST literals for `Vale.Terms`.
  Add the exact phrase to the vocabulary (e.g. `package\.json` stops `json` in it from
  being flagged), or turn the rule off for that file in `vale.ini` in a `[**/file.py]`
  section (the `**/` also covers the module docstring's copy under
  `build/vale_docstrings/`), with a one-line comment giving the reason.
- Turn a rule off everywhere in `vale.ini`, with a one-line comment giving the reason.

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

### Pipeline Benchmark

CI runs `pixi run bench-check`: it benchmarks `Diagram.refresh()` headlessly with
`scripts/bench_pipeline.py` and compares the deterministic counts (comm opens, messages
and bytes in both directions, layouts) to `scripts/bench_baseline.json`. Any change
fails, in either direction. If the change is intended, run `pixi run bench-update` and
commit the baseline, so the diff shows reviewers what got cheaper or more expensive.
Timings are written to the job summary but not gated.

## Building Documentation

To build (and check the link health) of what _would_ go to `ipyelk.readthedocs.org`, we:

- build with `sphinx` and `myst-nb`
- check links with `pytest-check-links`

Spelling and prose are checked in the sources by `pixi run lint-vale`.

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
