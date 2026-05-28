# depfresh

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/hpamanji/depfresh/actions/workflows/ci.yml/badge.svg)](https://github.com/hpamanji/depfresh/actions/workflows/ci.yml)

A dependency scanner that finds and parses dependency manifests across many
ecosystems — then optionally checks registries to tell you what's out of date.

The scan itself is **offline and stdlib-only** (no third-party runtime
dependencies). Network access happens only when you ask for update checks, and
every registry endpoint is configurable so private/internal mirrors work too.

```console
$ depfresh --check-updates
Scanned: .
Found 3 manifest(s), 12 dependencies across 2 ecosystem(s): node, python  |  2 outdated

requirements.txt  [python/pip]
----------------------------------
  requests  ==2.28.1  (runtime)  -> 2.31.0  [OUTDATED]
  flask     >=2.0     (runtime)  up to date

frontend/package.json  [node/npm]
----------------------------------
  react  ^18.2.0  (runtime)  -> 19.0.0  [OUTDATED]
```

## Features

- **Multi-ecosystem** — Python, Node, Go, Rust, Java/JVM, .NET, Ruby, and PHP.
- **Manifests and lockfiles** — reads both declared and resolved dependencies.
- **Outdated detection** — `--check-updates` queries each registry in parallel
  and flags stale pins.
- **Bump plan** — `--bump-plan` groups outdated packages across every file that
  pins them, ordered by blast radius.
- **Private registries** — point any ecosystem at Artifactory, Nexus, Azure
  Artifacts, devpi, Verdaccio, … with token or basic auth.
- **Scriptable** — `--json` for machine-readable output, `--exit-code` to fail
  CI when something is outdated.
- **Resilient** — a malformed manifest is reported per-file, never aborting the
  whole scan.

## Supported ecosystems

| Ecosystem | Manager  | Manifests parsed                                                                              | Registry for updates |
|-----------|----------|----------------------------------------------------------------------------------------------|----------------------|
| Python    | pip      | `requirements*.txt`, `constraints*.txt`, `pyproject.toml` (PEP 621 + Poetry), `Pipfile`, `Pipfile.lock`, `poetry.lock` | PyPI |
| Node      | npm      | `package.json`, `package-lock.json`                                                           | npm registry |
| Go        | go       | `go.mod`                                                                                      | proxy.golang.org |
| Rust      | cargo    | `Cargo.toml`, `Cargo.lock`                                                                    | crates.io |
| Java/JVM  | maven/gradle | `pom.xml`, `build.gradle`, `build.gradle.kts`                                             | Maven Central |
| .NET      | nuget    | `*.csproj`/`*.fsproj`/`*.vbproj`, `packages.config`, `Directory.Packages.props`, `packages.lock.json` | nuget.org |
| Ruby      | bundler  | `Gemfile`, `Gemfile.lock`                                                                     | rubygems.org |
| PHP       | composer | `composer.json`, `composer.lock`                                                              | Packagist |

## Installation

Requires **Python 3.11+** (it relies on the stdlib `tomllib`).

Install the latest from GitHub:

```console
pip install git+https://github.com/hpamanji/depfresh.git
```

Or from a clone:

```console
git clone https://github.com/hpamanji/depfresh.git
cd depfresh
pip install .
```

This installs a `depfresh` command. You can also run it without installing via
`python -m depfresh`.

## Usage

```console
depfresh [PATH] [OPTIONS]
```

`PATH` is a file or directory (default: the current directory). Pointing at a
single manifest scans just that file.

### Examples

```console
# List every dependency found under the current directory (grouped by file)
depfresh

# Scan a specific project, only Python and Node
depfresh ~/code/myapp -e python -e node

# Check registries and show only what's outdated
depfresh --outdated-only

# Produce a package-centric upgrade plan across all manifests
depfresh --bump-plan

# Machine-readable output for tooling
depfresh --json --check-updates

# Fail a CI job if anything is out of date
depfresh --check-updates --exit-code

# Just list the manifest files that were detected
depfresh --manifests-only

# One flat record per package, paired with its source file
depfresh --flat
```

### Options

| Option | Description |
|--------|-------------|
| `--json` / `--no-json` | Emit results as JSON instead of a table. |
| `-e`, `--ecosystem NAME` | Only report this ecosystem (repeatable). |
| `--manifests-only` | List detected manifest files without their dependencies. |
| `--flat` | One flat record per package, paired with its source file. |
| `-u`, `--check-updates` | Query registries for the latest version (network). |
| `--outdated-only` | Show only outdated dependencies (implies `--check-updates`). |
| `--bump-plan` | Group outdated deps by package across manifests (implies `--check-updates`). |
| `--timeout SECONDS` | Per-request registry timeout (default: 10). |
| `--jobs N` | Parallel registry requests (default: 16). |
| `--config PATH` | Path to a config file (default: auto-discover). |
| `--registry ECO=URL` | Override a registry base URL (repeatable). |
| `--registry-token ECO=TOKEN` | Bearer token for a registry (repeatable). |
| `--exit-code` | Exit with status 1 if any outdated dependency is found. |
| `--version` | Print the version and exit. |

Boolean flags use the `--flag`/`--no-flag` form, so a value enabled in a config
file can be overridden from the command line in either direction.

## Configuration

depfresh runs against public registries out of the box. To target private
mirrors or set default options, configure it via a JSON file, environment
variables, or CLI flags. Precedence (lowest to highest):

```
built-in defaults  <  config file(s)  <  environment  <  CLI flags
```

Config files are auto-discovered from `depfresh.json` / `.depfresh.json` in the
scanned project, then `~/.depfresh.json` and `~/.config/depfresh/config.json`.

```jsonc
{
  "settings": {
    "check-updates": true,
    "ecosystem": ["python", "node"]
  },
  "registries": {
    "python": {
      "base_url": "https://artifactory.acme.com/api/pypi/pypi-remote",
      "token": "${PYPI_TOKEN}"
    },
    "node": {
      "base_url": "https://artifactory.acme.com/api/npm/npm-remote",
      "username": "ci",
      "password": "${NPM_PASSWORD}"
    }
  }
}
```

`${VAR}` in any string is expanded from the environment, keeping secrets out of
the file.

Environment variables (`<ECO>` is the upper-cased ecosystem, e.g. `PYTHON`):

| Variable | Purpose |
|----------|---------|
| `DEPFRESH_REGISTRY_<ECO>` | Base URL |
| `DEPFRESH_TOKEN_<ECO>` | Bearer token |
| `DEPFRESH_USERNAME_<ECO>` | Basic-auth user |
| `DEPFRESH_PASSWORD_<ECO>` | Basic-auth password |

## How it works

1. **Scan** — walk the directory tree (skipping VCS dirs, virtualenvs, and
   vendored trees like `node_modules`), match each file to a parser, and parse
   it into structured `Dependency` records. This step touches no network.
2. **Check** (optional) — for each unique `(ecosystem, name)` look up the latest
   version from the relevant registry, in parallel, and compare it against the
   pinned constraint.

Version comparison is **best-effort**: it handles the dotted-numeric +
pre-release shape that covers the vast majority of real versions (PEP 440,
SemVer, NuGet, Maven), but it is not a full implementation of any one
ecosystem's spec. Treat the "outdated" flag as a strong hint, not a guarantee.

## Contributing

Contributions are very welcome — adding a new ecosystem is often just one parser
class and a couple of tests. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the
development setup and a step-by-step guide, and please review our
[Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE) © Hemachandar Pamanji
