# Scanning a project

Scanning is the offline core: depfresh walks a directory tree, matches files to
parsers, and turns each manifest into structured dependency records. It never
touches the network.

```console
depfresh [PATH]
```

`PATH` is a file or directory (default: current directory). Pointing at a single
manifest scans just that file.

## What gets scanned

depfresh descends the tree but skips noise: VCS metadata (`.git`, `.hg`, …),
virtualenvs (`.venv`, `venv`, `env`), caches (`__pycache__`, `.mypy_cache`, …),
and vendored trees (`node_modules`, `vendor`, `target`, `build`, `dist`). Those
hold transitive/third-party manifests, not your declared dependencies.

A manifest that fails to parse is reported against that one file — the rest of
the scan still succeeds.

## Output modes

### Table (default)

```console
$ depfresh
Scanned: .
Found 2 manifest(s), 5 dependencies across 2 ecosystem(s): node, python

requirements.txt  [python/pip]
----------------------------------
  requests  ==2.28.1  (runtime)
  flask     >=2.0     (runtime)

frontend/package.json  [node/npm]
----------------------------------
  react      ^18.2.0  (runtime)
  react-dom  ^18.2.0  (runtime)
  jest       ^29.0.0  (dev)
```

Each row is `name  version-constraint  (scope)`. Scope is one of `runtime`,
`dev`, `optional`, `peer`, `build`, `test`, `indirect`.

### JSON

```console
depfresh --json
```

```json
{
  "root": ".",
  "summary": { "manifest_count": 2, "dependency_count": 5, "ecosystems": ["node", "python"] },
  "manifests": [
    {
      "path": "requirements.txt",
      "ecosystem": "python",
      "manager": "pip",
      "dependencies": [
        { "name": "requests", "version": "==2.28.1", "ecosystem": "python", "scope": "runtime" }
      ],
      "error": null
    }
  ]
}
```

### Flat

One record per package, paired with its source file — handy for spreadsheets or
deduping across a monorepo:

```console
$ depfresh --flat
Scanned: .
3 package record(s)

  jest   ^29.0.0  dev      node    frontend/package.json
  react  ^18.2.0  runtime  node    frontend/package.json
  flask  >=2.0    runtime  python  requirements.txt
```

The flat JSON form keeps the `manifest` field on every record:

```console
depfresh --flat --json
```

### Manifests only

List which manifest files were detected, without their dependencies:

```console
depfresh --manifests-only
```

## Filtering by ecosystem

Restrict the report to one or more ecosystems (repeatable, case-insensitive):

```console
depfresh -e python -e node
```

## Notes on version constraints

depfresh records the constraint **exactly as written** in the manifest
(`^1.2.3`, `>=2,<3`, `~> 4.0`). It is `null` when the manifest pins no version
(e.g. a bare `flask` in requirements.txt, or a centrally managed .NET package).

To compare those constraints against the latest release, see
[Checking for updates](checking-updates.md).
