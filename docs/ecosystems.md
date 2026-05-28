# Supported ecosystems

Each ecosystem has one or more **parsers** (read manifests), a **registry**
client (look up the latest version for `--check-updates`), and **editors** (write
the new version back for `depfresh update`).

| Ecosystem | Manager | Manifests parsed | Registry | Editable by `update` |
|-----------|---------|------------------|----------|----------------------|
| Python | pip / pipenv / poetry | `requirements*.txt`, `constraints*.txt`, `pyproject.toml` (PEP 621 + Poetry), `Pipfile`, `Pipfile.lock`, `poetry.lock` | PyPI | `requirements*.txt`, `pyproject.toml`, `Pipfile` |
| Node | npm | `package.json`, `package-lock.json` | npm registry | `package.json` |
| Go | go | `go.mod` | proxy.golang.org | `go.mod` |
| Rust | cargo | `Cargo.toml`, `Cargo.lock` | crates.io | `Cargo.toml` |
| Java/JVM | maven / gradle | `pom.xml`, `build.gradle`, `build.gradle.kts` | Maven Central | `pom.xml`, `build.gradle*` |
| .NET | nuget | `*.csproj`/`*.fsproj`/`*.vbproj`, `packages.config`, `Directory.Packages.props`, `packages.lock.json` | nuget.org | project files, `packages.config`, `Directory.Packages.props` |
| Ruby | bundler | `Gemfile`, `Gemfile.lock` | rubygems.org | `Gemfile` |
| PHP | composer | `composer.json`, `composer.lock` | Packagist | `composer.json` |

## Lockfiles

Lockfiles are **parsed** (so scans and update checks see resolved versions) but
intentionally **not edited** by `depfresh update`. Bumping a declared manifest
without regenerating its lockfile via the real package manager would produce an
inconsistent lockfile, so depfresh leaves them to you.

## Scopes

Dependencies are tagged with a scope, normalized across ecosystems:

`runtime`, `dev`, `optional`, `peer`, `build`, `test`, `indirect`.

For example npm `devDependencies` → `dev`, `peerDependencies` → `peer`; Cargo
`build-dependencies` → `build`; go `// indirect` → `indirect`; Maven `<scope>`
is carried through.

## Private and self-hosted registries

Every registry base URL and its auth is configurable, so private mirrors
(Artifactory, Nexus, Azure Artifacts, devpi, Verdaccio, …) work the same way.
See [Configuration](configuration.md).

## Adding an ecosystem

Support is intentionally easy to extend — usually a parser plus a couple of
tests, optionally a registry client and an editor. See
[Extending depfresh](extending.md).
