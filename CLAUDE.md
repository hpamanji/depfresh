# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## Project

depfresh is a **stdlib-only** dependency scanner. It finds and parses dependency
manifests across ecosystems, checks registries for newer versions, and can open
update PRs/MRs (`depfresh update`). Full documentation lives in [`docs/`](docs/).

## Commands

Dev setup (editable install + dev tools):

```bash
pip install -e ".[dev]"
```

Quality gates — all four must pass (CI enforces them):

```bash
ruff check src tests
ruff format --check src tests
mypy src/depfresh
pytest --cov=depfresh --cov-fail-under=85
```

Run the CLI without installing (src layout):

```bash
PYTHONPATH=src python -m depfresh --help
PYTHONPATH=src python -m depfresh update --help
```

`conftest.py` puts `src/` on `sys.path` for pytest, so a plain `pytest` works.

## Layout

```
src/depfresh/
  scanner.py     walk a tree, dispatch files to parsers (offline)
  parsers/       manifest text -> Dependency  (registered in parsers/registry.py)
  resolver.py    registry clients + parallel check_updates (the network step)
  bump.py        group outdated deps into a BumpPlan
  editors/       format-preserving version write-back (editors/registry.py)
  vcs.py         thin git CLI wrapper
  forge/         GitHub + GitLab PR/MR clients
  updater.py     run_update: clone -> bump -> push -> open PR/MR
  config.py      merge config from files + env + CLI; registry/forge auth
  cli.py         `depfresh` (scan) and `depfresh update`
  models.py      Dependency / ManifestResult / ScanResult
tests/           one file per area, mirroring the package
```

See [docs/architecture.md](docs/architecture.md) for the full pipeline.

## Conventions / invariants

- **Stdlib only at runtime.** No third-party runtime dependencies (uses
  `tomllib`, `json`, `xml.etree`, `urllib`, `subprocess`). Dev-only: pytest,
  ruff, mypy.
- **Never crash a scan.** Parsers may raise on malformed input; the scanner
  records the error against that one manifest and continues. Don't add broad
  error handling inside parsers.
- **Editors are text-level.** They rewrite a single version in place to preserve
  comments/formatting — never parse-and-reserialize. Lockfiles are parsed but
  never edited.
- **Constraints are stored verbatim** as written in the manifest; extraction and
  comparison live in `versioning.py` and are best-effort, not spec-complete.
- **Style:** type hints everywhere, `from __future__ import annotations`, line
  length 100. `ruff` and `mypy` must pass.
- **Tests are offline.** Inject `fetch` (registry), `request` (forge), `forge`,
  and `clone_url` to avoid the network; git tests run against a local bare repo.

## Extending

Adding a parser, registry, editor, or forge is small and documented in
[docs/extending.md](docs/extending.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Git / pull requests

- `main` is protected and requires the **`CI success`** check; land changes via a
  pull request, not direct pushes.
- Keep commit messages factual and imperative. **Do not add AI/Claude co-author
  trailers** to commits.
