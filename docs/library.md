# Library API

Everything the CLI does is available as a Python API. The package is typed
(ships `py.typed`), so editors and mypy see full type information.

```python
import depfresh
```

## Scan a tree

```python
from depfresh import scan

result = scan("path/to/project")          # ScanResult
print(result.dependency_count, result.ecosystems)

for manifest in result.manifests:
    print(manifest.path, manifest.ecosystem, manifest.manager)
    for dep in manifest.dependencies:
        print(" ", dep.name, dep.version, dep.scope)

payload = result.to_dict()                # JSON-ready dict
```

`scan` is offline. Parse errors are recorded per manifest
(`ManifestResult.error`) rather than raised.

## Check for updates

```python
from depfresh import scan, check_updates

result = scan(".")
updates = check_updates(result)           # dict[(ecosystem, name) -> UpdateInfo]

for (eco, name), info in updates.items():
    print(eco, name, info.current, "->", info.latest, info.status)
```

`check_updates` performs the network lookups (parallel, deduplicated). Pass a
`config=DepfreshConfig(...)` for private registries, or inject `fetch=...` (a
`fetch(url, headers) -> str` callable) to test without the network.

## Build a bump plan

```python
from depfresh import scan, check_updates, build_bump_plan

result = scan(".")
plan = build_bump_plan(result, check_updates(result))

for item in plan.items:                   # most-impactful first
    print(item.name, "->", item.latest, f"({item.manifest_count} files)")
    for occ in item.occurrences:
        print("   ", occ.manifest, occ.current, occ.scope)
```

## Run an end-to-end update

```python
from depfresh import run_update

run = run_update(
    "https://github.com/me/app",
    token="ghp_…",
    grouping="all",          # "all" | "ecosystem" | "dependency"
    dry_run=True,            # preview; pushes/opens nothing
)
print(run.base_branch)
for group in run.groups:
    print(group.title, group.branch, group.files_changed, group.request_url)
```

`run_update` clones to a temp dir, reuses scan/check/bump, rewrites declared
manifests, and (unless `dry_run`) pushes and opens PR/MR(s). Injection points
for testing: `fetch` (registry), `request` (forge HTTP), `forge` (a `Forge`
instance), and `clone_url` (e.g. a local bare repo).

## Loading configuration

```python
from depfresh import load_config, check_updates, scan

config = load_config(scan_path=".")       # merges files + environment
updates = check_updates(scan("."), config=config)
```

You can also build config objects directly:

```python
from depfresh import DepfreshConfig, RegistryConfig, ForgeConfig

config = DepfreshConfig(
    registries={"python": RegistryConfig(base_url="https://pypi.acme.com", token="…")},
    forges={"github": ForgeConfig(token="ghp_…")},
)
```

## Key types

| Type | Where | Notes |
|------|-------|-------|
| `Dependency` | `depfresh.models` | `name`, `version`, `ecosystem`, `scope`, `manifest`. |
| `ManifestResult` | `depfresh.models` | One parsed manifest (`path`, `manager`, `dependencies`, `error`). |
| `ScanResult` | `depfresh.models` | Aggregate; `dependency_count`, `ecosystems`, `to_dict()`. |
| `UpdateInfo` | `depfresh.resolver` | `current`, `current_version`, `latest`, `status`, `error`. |
| `BumpPlan` / `BumpItem` | `depfresh.bump` | Package-centric update plan. |
| `UpdateRun` / `UpdateGroup` | `depfresh.updater` | Result of `run_update`. |
| `DepfreshConfig` / `RegistryConfig` / `ForgeConfig` | `depfresh.config` | Configuration. |

See [Architecture](architecture.md) for how these fit together.
