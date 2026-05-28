# Checking for updates

Adding `--check-updates` (or `-u`) makes depfresh query each ecosystem's registry
for the latest version and compare it against your pinned constraint. This is the
only step that uses the network.

```console
depfresh --check-updates
```

Lookups are deduplicated per `(ecosystem, name)` and run in parallel.

## Statuses

Each dependency gets one of:

| Status | Meaning |
|--------|---------|
| `outdated` | A newer version exists than the pinned one. |
| `current` | The pin already matches the latest. |
| `unknown` | The registry was reachable, but the constraint had no comparable version (wildcard, URL, centrally managed). |
| `not_found` | The package isn't in the registry. |
| `error` | A network or parse failure during lookup. |

```console
$ depfresh --check-updates
Scanned: .
Found 1 manifest(s), 2 dependencies across 1 ecosystem(s): python  |  1 outdated

requirements.txt  [python/pip]
----------------------------------
  requests  ==2.28.1  (runtime)  -> 2.31.0  [OUTDATED]
  flask     >=2.0     (runtime)  up to date
```

## Show only what's outdated

```console
depfresh --outdated-only
```

Implies `--check-updates` and filters every view (table, JSON, flat) down to
outdated dependencies.

## Bump plan

`--bump-plan` flips the file-centric view into a **package-centric** one: one
entry per outdated package, listing every file that pins it, ordered by blast
radius (most files first).

```console
$ depfresh --bump-plan
Scanned: .
Bump plan: 2 package(s) to update across 3 manifest(s)

requests  ->  2.31.0   [python]  (2 files)
    services/api/requirements.txt  ==2.28.1  (runtime)
    services/web/requirements.txt  ==2.30.0  (runtime)

react  ->  19.0.0   [node]  (1 file)
    frontend/package.json  ^18.2.0  (runtime)
```

JSON form:

```console
depfresh --bump-plan --json
```

## Use in CI

Exit non-zero when anything is outdated, so a CI job can gate on freshness:

```console
depfresh --check-updates --exit-code
```

## Tuning network behaviour

| Flag | Default | Purpose |
|------|---------|---------|
| `--timeout SECONDS` | 10 | Per-request registry timeout. |
| `--jobs N` | 16 | Parallel registry requests. |

## Private registries

Update checks honour per-ecosystem base URLs and auth. See
[Configuration](configuration.md) for config files, environment variables, and
the `--registry` / `--registry-token` flags.

## Version comparison is best-effort

depfresh handles the dotted-numeric + pre-release shape that covers the vast
majority of real versions (PEP 440, SemVer, NuGet, Maven). It is not a full
implementation of any one ecosystem's spec, so treat `outdated` as a strong
hint, not a guarantee.
