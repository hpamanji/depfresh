# Architecture

depfresh is a small pipeline of focused modules. A run flows left to right; only
the network stages touch anything outside the working tree.

```
                        (offline)                 (network)            (network + git)
 path ──► scanner.scan ──► ScanResult ──► resolver.check_updates ──► bump.build_bump_plan
                                                                              │
                                                                              ▼
                                                            updater.run_update (depfresh update)
                                                       clone ─► editors ─► vcs ─► forge (PR/MR)
```

## Modules

The modules split across two packages: the MIT **`depfresh`** core (scan → check
→ bump-plan) and the AGPL/commercial **`depfresh-pro`** add-on (the `update`
automation). The core never imports pro; `depfresh update` is wired in at runtime
via the `depfresh.commands` entry point.

| Package | Module | Responsibility |
|---------|--------|----------------|
| `depfresh` | `scanner.py` | Walk a tree, skip ignored dirs, dispatch files to parsers. |
| `depfresh` | `parsers/` | One family per module; manifest text → `Dependency` objects. Registered in `parsers/registry.py` (`PARSERS`). |
| `depfresh` | `models.py` | `Dependency`, `ManifestResult`, `ScanResult` dataclasses. |
| `depfresh` | `versioning.py` | Best-effort version extraction, comparison, and `bump_constraint`. |
| `depfresh` | `resolver.py` | Per-ecosystem registry clients + parallel `check_updates`. The only place the base scan's network lives. |
| `depfresh` | `bump.py` | Group outdated deps into a package-centric `BumpPlan`. |
| `depfresh` | `config.py` | Merge config from files + env + CLI; registry and forge auth. |
| `depfresh` | `cli.py` | argparse front end for `depfresh` (scan); dispatches add-on commands. |
| `depfresh-pro` | `editors/` | Format-preserving version write-back; registered in `editors/registry.py` (`EDITORS`). |
| `depfresh-pro` | `vcs.py` | Thin `git` CLI wrapper (clone/branch/commit/push). |
| `depfresh-pro` | `forge/` | GitHub + GitLab PR/MR clients behind a `Forge` interface. |
| `depfresh-pro` | `updater.py` | Orchestrate clone → bump → push → open MR. |
| `depfresh-pro` | `cli.py` | The `depfresh update` subcommand (entry point). |

## Design principles

- **Stdlib only at runtime.** Scanning, checking, and updating use just the
  standard library (`tomllib`, `json`, `xml.etree`, `urllib`, `subprocess`).
- **Never crash a scan.** Parsers may raise on malformed input; the scanner
  records the error against that one manifest and continues.
- **Best-effort, not perfect.** Version handling is approximate by design —
  simple rules that are right the vast majority of the time.
- **Constraints kept verbatim.** The pin is stored exactly as written;
  extraction/comparison/bumping happen later in `versioning.py`.
- **Injectable I/O.** Network and git are passed in as callables/objects
  (`fetch`, `request`, `forge`, `clone_url`) so the whole flow is testable
  offline — see the test suite for the patterns.

## Parsers vs. editors

`parsers/` and `editors/` mirror each other but pull in opposite directions:

- A **parser** reads a manifest into structured data (it may reorder/normalize).
- An **editor** rewrites a single version *in place* using text-level
  replacement, so comments and formatting survive. Editors exist only for
  **declared** manifests; lockfiles are parsed but never edited.

## Reading the code

A good path through the codebase: `models.py` → `parsers/base.py` →
`scanner.py` → `resolver.py` → `bump.py` → `editors/base.py` → `updater.py` →
`cli.py`. To add support for something new, see
[Extending depfresh](extending.md).
