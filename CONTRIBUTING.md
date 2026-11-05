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

- `master`: the `3.x` development line, which distributes the lab extension inside the
  python distribution for JupyterLab `>=4.1,<5`
  - generates the `latest` tag on ReadTheDocs

## Important Paths

| Path                                 | Purpose                                              |
| ------------------------------------ | ---------------------------------------------------- |
| `atest/`                             | Robot Framework source for acceptance tests          |
| `pixi.toml`                          | task automation tool                                 |
| `pixi.lock`                          | pinned build/test/docs environments                  |
| `js/`                                | TypeScript source for `@jupyrdf/jupyter-elk`         |
| `package.json/`                      | `npm` package description for `@jupyrdf/jupyter-elk` |
| `pyproject.toml`                     | package description for `ipyelk`                     |
| `src/`                               | Python source for `ipyelk`                           |
| `src/ipyelk/schema/elkschema.json`   | JSON schema derived from the TypeScript source       |
| `src/ipyelk/schema/elk-catalog.json` | ELK layout options known to the bundled `elkjs`      |
| `yarn.lock`                          | frozen `npm` dependencies                            |
| `docs/`                              | documentation                                        |
| `examples/`                          | examples, used in demo and test                      |
| `lite/`                              | JupyterLite demo configuration                       |

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

### Work Markers

A `TODO`, `FIXME`, `XXX` or `HACK` comment names the GitHub issue that tracks it:
`TODO(#123): what to do`. `pixi run lint-todos` (part of `pixi run lint`) fails on a
marker without an issue number, and on a `todo:` or `fixme:` in lower case. Open the
issue first, then write the marker. `git grep "TODO(#"` lists them all.

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

`pixi run release` builds and checks the project; it does not publish packages. It also
runs `fix`, which can change tracked files. Review and commit those changes before
qualifying a release. Publication remains a separate maintainer action.

### Prepare and qualify a candidate

1. Open a release PR updating `pyproject.toml` and `package.json`, the dated changelog,
   and migration guidance. Keep Python and npm versions synchronized:

   | Release   | Python     | npm         |
   | --------- | ---------- | ----------- |
   | Candidate | `3.0.0rc1` | `3.0.0-rc1` |
   | Final     | `3.0.0`    | `3.0.0`     |

   The widget module requirement converts Python `rc1` to npm `-rc1`. `3.0.0-rc.1` does
   not satisfy that exact requirement. Do not bump a version just to rebuild an already
   published release.

2. Run `pixi run release` and review any resulting changes. Merge the reviewed release
   PR, then select the successful **CI** run for that exact `master` commit. Record its
   full commit SHA, run ID and run number. Require every release check to pass; inspect
   acceptance reports and retry logs for failures hidden by retries or skips. Review the
   changelog's known issues before deciding whether the candidate meets the
   final-release threshold.
3. Download only that run's `ipyelk-<run-number>-dist` artifact into a new, empty
   directory. For example, with GitHub CLI, substitute the recorded values:

   ```bash
   gh run view <run-id> --repo jupyrdf/ipyelk --json headSha,conclusion,url
   gh run download <run-id> --repo jupyrdf/ipyelk \
     --name ipyelk-<run-number>-dist --dir <artifact-directory>
   ```

   Check `headSha` against the recorded release commit and `conclusion` against
   `success`. The artifact contains `dist/` and task-cache metadata; publish only the
   distribution files inside `dist/`. It must contain one wheel, one source archive, one
   npm tarball and `SHA256SUMS`, all for the intended version.

4. Verify the downloaded files against `dist/SHA256SUMS` from inside `dist/`:

   ```bash
   shasum -a 256 -c SHA256SUMS
   ```

   Inspect the Python metadata and `package/package.json` in the npm tarball: their
   versions must match the release PR. Keep the run URL and `SHA256SUMS` with the
   release record. In a fresh environment, install the downloaded wheel and its
   dependencies, check `jupyter labextension list`, and exercise the interactive
   examples in JupyterLab. Confirm the installed versions and test the documented
   upstream widget limitations. Do not substitute a development install for this package
   smoke test.

### Tag and publish the verified files

Use a clean checkout of the recorded release commit. Confirm `git rev-parse HEAD`
matches it, then create and push only the intended tag (historically `v2.1.1`; for
example, `v3.0.0rc1` or `v3.0.0`). Check `git remote -v` and choose the release remote
pointing to `jupyrdf/ipyelk`. Substitute the recorded values below:

```bash
git tag -a v<python-version> <release-commit-sha> -m "ipyelk <python-version>"
git push <release-remote> refs/tags/v<python-version>
```

Authenticate to PyPI and npm using the maintainers' configured credentials. Publish
explicit downloaded files, without rebuilding or publishing the working directory:

```bash
npm publish <artifact-directory>/dist/jupyrdf-jupyter-elk-<npm-version>.tgz --tag next
twine upload <artifact-directory>/dist/ipyelk-<python-version>-py3-none-any.whl \
  <artifact-directory>/dist/ipyelk-<python-version>.tar.gz
```

Use npm's `next` tag for a candidate and `latest` for a final release. Do not use
`jlpm publish` or `yarn publish`: they can omit distribution files. If publication
partially succeeds, inspect both registries before retrying; do not overwrite or rebuild
a published version.

Create the GitHub release from the exact tag. For a candidate, use the
`gh release create` option `--prerelease`. Attach the verified distributions and
`SHA256SUMS`. Include migration guidance, known limitations and the qualifying CI run.
Verify the published package versions and ReadTheDocs build; point stable documentation
at the final release only after its validation.

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
