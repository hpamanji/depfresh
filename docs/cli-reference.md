# CLI reference

depfresh has two commands:

- `depfresh [PATH]` — scan and (optionally) check for updates.
- `depfresh update <REPO_URL>` — clone, bump, and open PRs/MRs.

Boolean flags use the `--flag` / `--no-flag` form, so a value enabled in a config
file can be overridden on the command line in either direction. Any flag left
unset falls back to the config file, then the built-in default.

## `depfresh [PATH]`

Scan `PATH` (a file or directory; default: current directory) for dependency
manifests.

| Option | Default | Description |
|--------|---------|-------------|
| `PATH` | `.` | File or directory to scan. |
| `--json` / `--no-json` | off | Emit results as JSON instead of a table. |
| `-e`, `--ecosystem NAME` | all | Only report this ecosystem (repeatable). |
| `--manifests-only` | off | List detected manifest files without their dependencies. |
| `--flat` | off | One flat record per package, paired with its source file. |
| `-u`, `--check-updates` | off | Query registries for the latest version (network). |
| `--outdated-only` | off | Show only outdated deps (implies `--check-updates`). |
| `--bump-plan` | off | Package-centric plan across manifests (implies `--check-updates`). |
| `--timeout SECONDS` | 10 | Per-request registry timeout. |
| `--jobs N` | 16 | Parallel registry requests. |
| `--config PATH` | auto | Path to a depfresh JSON config file. |
| `--registry ECO=URL` | — | Override a registry base URL (repeatable). |
| `--registry-token ECO=TOKEN` | — | Bearer token for a registry (repeatable). |
| `--exit-code` | off | Exit `1` if any outdated dependency is found. |
| `--version` | — | Print the version and exit. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (and, with `--exit-code`, nothing outdated). |
| `1` | With `--exit-code`: at least one outdated dependency. |
| `2` | Usage / config / path error (message on stderr). |

## `depfresh update <REPO_URL>`

Clone the repo, bump outdated declared manifests, push branch(es), and open
PR/MR(s). Requires `git`.

| Option | Default | Description |
|--------|---------|-------------|
| `REPO_URL` | — | Repository URL (https) to update. |
| `--token TOKEN` | env/config | Forge access token. |
| `--grouping all\|ecosystem\|dependency` | `all` | How to split updates into MRs. |
| `--base BRANCH` | repo default | Target branch for the MR. |
| `-e`, `--ecosystem NAME` | all | Only update this ecosystem (repeatable). |
| `--exclude PKG` | — | Leave a package untouched (repeatable). |
| `--branch-prefix P` | `depfresh/` | Branch name prefix. |
| `--dry-run` / `--no-dry-run` | off | Show changes/MRs without pushing or opening. |
| `--json` / `--no-json` | off | Emit the result as JSON. |
| `--timeout SECONDS` | 10 | Per-request registry timeout. |
| `--jobs N` | 16 | Parallel registry requests. |
| `--config PATH` | auto | Path to a depfresh JSON config file. |
| `--registry ECO=URL` | — | Override a registry base URL (repeatable). |
| `--registry-token ECO=TOKEN` | — | Bearer token for a registry (repeatable). |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (MRs opened, or dry run printed). |
| `2` | Usage / config / git / forge error (message on stderr). |

## Running without installing

```console
python -m depfresh --help
python -m depfresh update --help
```

See [Configuration](configuration.md) for environment variables and config
files, and [Updating dependencies](updating.md) for the update workflow.
