# Quickstart

Five common tasks, each a one-liner. Deeper detail lives in the linked guides.

## 1. List every dependency in a project

```console
depfresh
```

Scans the current directory and prints a table grouped by manifest file. Point
it elsewhere with a path:

```console
depfresh ~/code/myapp
```

→ More in [Scanning a project](scanning.md).

## 2. Find out what's outdated

```console
depfresh --outdated-only
```

Queries each ecosystem's registry in parallel and shows only dependencies that
have a newer version.

→ More in [Checking for updates](checking-updates.md).

## 3. Get machine-readable output

```console
depfresh --json --check-updates > report.json
```

Every command supports `--json` for piping into other tools.

## 4. Fail CI when something is outdated

```console
depfresh --check-updates --exit-code
```

Exits `1` if any dependency is outdated, `0` otherwise — drop it into a CI step.

## 5. Open update PRs/MRs automatically

```console
# Preview first — clones and edits locally, pushes nothing
depfresh update https://github.com/me/app --token "$GITHUB_TOKEN" --dry-run

# Then open a single PR with all the bumps
depfresh update https://github.com/me/app --token "$GITHUB_TOKEN"
```

→ More in [Updating dependencies](updating.md).

## Next steps

- Targeting a private registry or a self-hosted forge? See
  [Configuration](configuration.md).
- Want to script depfresh instead of shelling out? See the
  [Library API](library.md).
