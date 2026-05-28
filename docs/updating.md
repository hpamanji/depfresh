# Updating dependencies

> Provided by the **`depfresh-pro`** package (AGPL-3.0-or-later / commercial),
> not the MIT core. Install it (`pip install depfresh-pro`) to enable
> `depfresh update`. See [LICENSING.md](../LICENSING.md).

`depfresh update` closes the loop: it clones a repository, finds outdated
dependencies (the same scan → check → bump pipeline), rewrites the **declared
manifests** in place, pushes branch(es), and opens a pull request (GitHub) or
merge request (GitLab) against the default branch.

```console
depfresh update <REPO_URL> --token <TOKEN> [options]
```

Requires `git` on your `PATH`.

## Start with a dry run

`--dry-run` clones and applies edits locally, prints the diff and the MRs it
*would* open, and then pushes/opens nothing. Always the safe first step:

```console
depfresh update https://github.com/me/app --token "$GITHUB_TOKEN" --dry-run
```

```
Repository: https://github.com/me/app
Base branch: main
(dry run — no branches pushed, no MRs opened)

Update 2 dependencies
  branch: depfresh/updates
  files:  frontend/package.json, requirements.txt
  (not pushed)
```

## Open the request(s)

Drop `--dry-run` to push and open for real:

```console
depfresh update https://github.com/me/app --token "$GITHUB_TOKEN"
```

```
Repository: https://github.com/me/app
Base branch: main

Update 2 dependencies
  branch: depfresh/updates
  files:  frontend/package.json, requirements.txt
  MR:     https://github.com/me/app/pull/42
```

## Grouping

`--grouping` controls how bumps are split into branches/MRs (default: `all`).

| Mode | Result |
|------|--------|
| `all` (default) | One branch + one MR with every outdated dep. |
| `ecosystem` | One branch + MR per ecosystem (`depfresh/python-updates`, …). |
| `dependency` | One branch + MR per package (`depfresh/react-19.0.0`, …) — Dependabot-style. |

```console
depfresh update https://gitlab.com/me/app --token "$GITLAB_TOKEN" --grouping dependency
```

## What gets changed (and what doesn't)

- **Declared manifests are rewritten**, preserving comments and formatting —
  `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`,
  `pom.xml`, `build.gradle`, `*.csproj`, `composer.json`, `Gemfile`, etc.
- The version's operator/prefix is kept: `^18.2.0` → `^19.0.0`, `==2.28.1` →
  `==2.31.0`, `v1.2.3` → `v1.9.0`.
- **Lockfiles are left untouched.** Regenerate them with your package manager
  (`npm install`, `poetry lock`, `cargo update`, …) — depfresh stays
  toolchain-free.

## Useful options

| Option | Description |
|--------|-------------|
| `--token TOKEN` | Forge access token (else `DEPFRESH_FORGE_TOKEN_<KIND>` or config). |
| `--grouping all\|ecosystem\|dependency` | How to split updates (default: `all`). |
| `--base BRANCH` | Target branch for the MR (default: the repo's default branch). |
| `--exclude PKG` | Leave a package untouched (repeatable). |
| `-e, --ecosystem NAME` | Only update this ecosystem (repeatable). |
| `--branch-prefix P` | Branch name prefix (default: `depfresh/`). |
| `--delete-branch` / `--no-delete-branch` | Delete update branches once their PR/MR merges (default: enabled). |
| `--dry-run` | Show changes and planned MRs without pushing or opening. |
| `--json` | Emit the result as JSON. |

## Authentication

The token needs permission to **push branches** and **open PRs/MRs**.

- Pass it with `--token`, or set `DEPFRESH_FORGE_TOKEN_GITHUB` /
  `DEPFRESH_FORGE_TOKEN_GITLAB`, or put it in a config file under `forges`.
- It is handed to git per-invocation via an `http.extraheader` and is **never
  written** to the clone's `.git/config`; the temporary clone is deleted when the
  run finishes.
- Self-hosted GitHub Enterprise / GitLab: set the API base URL and forge `kind`
  in config (see [Configuration](configuration.md)).

## Idempotency

Re-running `depfresh update` (e.g. on a schedule) never piles up duplicate
branches or MRs:

- **Fixed branch names.** A given update always uses the same branch —
  `depfresh/updates` (all), `depfresh/<ecosystem>-updates`, or `depfresh/<pkg>`
  (dependency). The package version appears only in the title, never the branch.
- **Reuse the open request.** depfresh looks up an already-open PR/MR for the
  branch and reuses it — refreshing its title/body to the current versions —
  instead of opening a second one.
- **Refresh the branch in place.** If a newer release lands, the same branch is
  force-updated (with lease) to the new versions.
- **No-op when nothing changed.** If the recomputed branch is identical to what's
  already pushed, depfresh skips the push and the API call entirely — clean
  re-runs, no CI churn.

## Branch cleanup

By default depfresh asks the forge to delete the update branch once its PR/MR
merges, so branches don't accumulate:

- **GitLab** — set per-MR via `remove_source_branch`.
- **GitHub** — there's no per-PR flag, so depfresh enables the repository's
  *"Automatically delete head branches"* setting (best-effort; needs admin on the
  token). This is repo-wide; disable with `--no-delete-branch` if you'd rather
  not change the setting.

## Limitations (v1)

- Constraint range handling is best-effort: for multi-clause ranges only the
  first version token is bumped, which can need manual review if the bump crosses
  an upper bound.
- HTTPS + token remotes only (no SSH).
- Manifests can drift from lockfiles until you regenerate them.
