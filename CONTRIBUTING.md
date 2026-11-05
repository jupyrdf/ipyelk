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

Merge a reviewed release PR to publish. Update `pyproject.toml`, `package.json`, the
dated changelog and migration guidance together. The release commit must change its
Python version relative to its first parent. Version mappings are:

| Release   | Python     | npm            | npm channel |
| --------- | ---------- | -------------- | ----------- |
| Alpha     | `3.0.0a1`  | `3.0.0-alpha1` | `next`      |
| Beta      | `3.0.0b1`  | `3.0.0-beta1`  | `next`      |
| Candidate | `3.0.0rc1` | `3.0.0-rc1`    | `next`      |
| Final     | `3.0.0`    | `3.0.0`        | `latest`    |

`pixi run release` builds and checks the project; it does not publish. It runs `fix`,
which can change tracked files. Review and commit those changes before merging.

### Automated publication

The `Release` workflow waits for successful `CI` on the exact merged `master` commit. It
requires all ten build, lint, documentation and platform test jobs to succeed. Inspect
acceptance reports and retry logs when qualifying a release; green CI can include the
documented automatic retries and known platform skips. Review the changelog's known
limitations against the intended release threshold.

The publisher downloads that run's immutable distribution artifact, verifies its archive
digest and `SHA256SUMS`, and checks the three distribution versions. It copies only the
wheel, source archive, npm tarball and manifest into its publication directory. It does
not rebuild or publish a working directory. The qualifying CI already runs
installed-wheel acceptance tests. An additional fresh environment checks the installed
Python package, extension registration and static assets; this short smoke check does
not repeat the browser acceptance suite.

The workflow publishes the verified npm tarball and Python files through trusted
publishing, verifies registry identities, then creates the exact-commit tag and GitHub
release with the distributions and `SHA256SUMS`. npm source provenance is disabled:
`workflow_run` can identify a newer workflow invocation commit than the CI commit that
built the downloaded package. OIDC still authenticates publication. The exact CI run,
artifact digest, distribution checksums and release tag establish the package identity;
the publisher does not claim that its invocation commit built those files. Candidates
are GitHub prereleases; final versions use npm `latest`. It runs only for commits
changing the release version, so ordinary development commits do not publish. Tags
created with `GITHUB_TOKEN` do not trigger another CI run; publication uses the
already-qualified master run instead.

If a step fails, rerun the workflow or dispatch `Release` with the original successful
CI `run_id`. Never rebuild an already-published version. Existing PyPI and npm files
must match the tested hashes before they count as published. Only missing Python files
are uploaded, and matching partial GitHub assets are completed without replacement.
Conflicting tags, versions, release channels or asset bytes fail before publication.
Registry authentication failures require correcting the account settings below, then
resuming the same run. Verify conda-forge and ReadTheDocs after publication; those are
separate services, and their completion is not implied by this workflow succeeding.

### One-time publishing settings

Configure these existing projects to trust GitHub Actions:

- PyPI project `ipyelk`: owner `jupyrdf`, repository `ipyelk`, workflow `release.yml`,
  environment `release`.
- npm package `@jupyrdf/jupyter-elk`: GitHub Actions owner `jupyrdf`, repository
  `ipyelk`, workflow `release.yml`, environment `release`.
- GitHub environment `release`: allow the default branch. To avoid routine manual
  approval, do not require a reviewer for this environment. The repository must allow
  its release job to write contents and request an OIDC token.

The workflow uses Node 24 and checks npm is at least 11.5.1. No long-lived PyPI or npm
publishing token is needed. See the official
[PyPI publisher settings](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
and [npm trusted publishing instructions](https://docs.npmjs.com/trusted-publishers/).
Repository files cannot establish whether these account settings already exist.

Conda-forge packages the published source archive through the canonical
[feedstock](https://github.com/conda-forge/ipyelk-feedstock). Keep its recipe
dependencies aligned with this project and enable its version-update automerge policy
after recipe CI passes. Stable PyPI publication lets the conda-forge version bot
discover releases; conda builds and publication remain under conda-forge's
infrastructure.

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
