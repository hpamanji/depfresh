# Contributing to depfresh

Thanks for your interest in improving depfresh! This project thrives on
community contributions, and adding support for a new ecosystem is usually a
small, self-contained change. Whether you're fixing a typo, reporting a bug, or
adding a whole new parser, you're welcome here.

By participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** — open an issue with a minimal manifest snippet that
  reproduces the problem.
- **Request a feature** — describe the use case; "I want depfresh to support X"
  is a great start.
- **Add an ecosystem** — a new parser (and optionally a registry client) is the
  highest-impact contribution. See [Adding a parser](#adding-a-parser) below.
- **Improve docs** — examples, clarifications, and fixes are always appreciated.

No contribution is too small. If you're unsure whether something is wanted, open
an issue first and ask — we'd rather discuss early than have you spend effort on
a change we can't merge.

## Development setup

depfresh has **no third-party runtime dependencies**; the only dev dependency is
`pytest`.

```console
git clone https://github.com/hpamanji/depfresh.git
cd depfresh
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Requires Python 3.11+ (the parsers use the stdlib `tomllib`).

## Running the tests

```console
pytest
```

The suite is fast (under a second) and runs fully offline — registry access in
tests goes through an injected fake `fetch`, never the network. Please add or
update tests for any behavior change, and make sure the whole suite is green
before opening a pull request.

## Project layout

```
src/depfresh/
  scanner.py         # walks a tree, dispatches files to parsers
  registry.py        # maps filenames -> parsers (register new parsers here)
  resolver.py        # registry clients + parallel "latest version" lookups
  versioning.py      # best-effort version extraction & comparison
  config.py          # config file / env / CLI merging, private-registry auth
  bump.py            # groups outdated deps into a package-centric plan
  cli.py             # argparse front end and output rendering
  models.py          # Dependency / ManifestResult / ScanResult dataclasses
  parsers/           # one module per ecosystem
tests/               # mirrors the package, one test file per area
```

## Design principles

Keep these in mind so your change fits the codebase:

- **Stdlib only at runtime.** The scan must work with a bare Python install.
  Don't add third-party runtime dependencies.
- **Never crash a scan.** Parsers may raise on malformed input — the scanner
  catches it and records the error against that one manifest. Don't add
  broad error handling inside parsers; let the scanner do its job.
- **Best-effort, not perfect.** Version handling is approximate by design.
  Prefer a simple rule that's right 95% of the time over a spec-complete parser.
- **Pinned versions are kept verbatim.** Store the constraint exactly as written
  in the manifest (`^1.2.3`, `>=2,<3`); extraction/comparison happens later in
  `versioning.py`.

## Adding a parser

Say you want to support a new ecosystem (or another manifest format for an
existing one):

1. **Create a module** under `src/depfresh/parsers/`, e.g. `elixir.py`.
2. **Subclass `Parser`** and declare which files it handles and how to parse
   them:

   ```python
   from depfresh.models import Dependency
   from depfresh.parsers.base import Parser

   class MixExsParser(Parser):
       ecosystem = "elixir"
       manager = "mix"
       filenames = ("mix.exs",)          # exact basenames
       # patterns = ("*.foo",)           # or fnmatch globs

       def parse(self, text: str) -> list[Dependency]:
           deps: list[Dependency] = []
           # ... parse `text` ...
           deps.append(self._dep("phoenix", "~> 1.7", scope="runtime"))
           return deps
   ```

   Use the `self._dep(name, version, scope=...)` helper — it trims whitespace
   and normalizes empty versions to `None`. Valid scopes include `runtime`,
   `dev`, `optional`, `peer`, `build`, `test`, and `indirect`.

3. **Register it** in `src/depfresh/registry.py` by adding an instance to the
   `PARSERS` tuple.
4. **Add tests** in `tests/test_parsers.py` with a representative manifest
   snippet, asserting names, versions, and scopes.

That's all that's needed for the offline scan to pick up the new format.

## Adding update checks for an ecosystem

To make `--check-updates` work for a new ecosystem, add a registry client in
`src/depfresh/resolver.py`:

1. **Subclass `Registry`**, set `ecosystem` and `default_base_url`, and
   implement `latest(self, name, fetch, config)` returning the newest version
   string (or `None`):

   ```python
   class HexRegistry(Registry):
       ecosystem = "elixir"
       default_base_url = "https://hex.pm/api/packages"

       def latest(self, name, fetch, config):
           url = f"{self.base(config)}/{name}"
           data = json.loads(fetch(url, config.auth_headers()))
           return data.get("latest_stable_version")
   ```

2. **Register it** in the `_REGISTRIES` map.
3. **Add tests** in `tests/test_resolver.py` using the `recording_fetch`
   helper, so no real network call is made.

Use `config.base_url` / `config.auth_headers()` so private registries and
authentication keep working for the new ecosystem.

## Adding an editor (for `depfresh update`)

`depfresh update` rewrites a dependency's version in place. Editors live in
`src/depfresh/editors/`, mirroring `parsers/`, and do **text-level** replacement
(never parse-and-reserialize, which would lose comments/formatting).

1. **Add an editor module** under `src/depfresh/editors/`, subclassing `Editor`
   and reusing a shared helper from `editors/base.py`
   (`replace_json_dependency`, `replace_toml_dependency`,
   `replace_requirements_dependency`, `replace_pom_dependency`,
   `replace_coordinate_dependency`, `replace_dotnet_dependency`,
   `replace_gomod_dependency`, `replace_gemfile_dependency`) — or a new helper:

   ```python
   from depfresh.editors.base import EditResult, Editor, replace_toml_dependency

   class MixExsEditor(Editor):
       ecosystem = "elixir"
       filenames = ("mix.exs",)

       def apply(self, text, name, current, latest) -> EditResult:
           return replace_toml_dependency(text, name, latest)  # returns (new_text, changed)
   ```

   New version strings are computed by `versioning.bump_constraint`, which
   preserves the operator/prefix (`^18.2.0` + `19.0.0` → `^19.0.0`).

2. **Register it** in `src/depfresh/editors/registry.py` (`EDITORS`). Only add
   editors for **declared** manifests — lockfiles must stay absent so they're
   skipped.
3. **Add tests** in `tests/test_editors.py`; assert formatting is preserved and,
   where possible, that the result re-parses to the new version.

## Coding style

- Type-hint public functions; modules start with
  `from __future__ import annotations`.
- Write a short module/class docstring explaining *why* a thing exists.
- Avoid comments that just restate the code; comment the non-obvious *why*.
- Match the surrounding style — small, focused functions, dataclasses for data.

## Pull request process

1. Fork the repo and create a branch from `main`
   (e.g. `feature/elixir-parser` or `fix/gemfile-scopes`).
2. Make your change with tests, and ensure `pytest` passes.
3. Use a clear, imperative commit message (e.g. "Add Elixir mix.exs parser").
4. Open a pull request describing **what** changed and **why**. Link any related
   issue.
5. A maintainer will review. Small, focused PRs are reviewed fastest — if you're
   planning something large, open an issue to discuss it first.

Thank you for helping make depfresh better!
