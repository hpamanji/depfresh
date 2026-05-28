# Configuration

depfresh works against public registries with zero config. Configure it when you
need private/internal registries, forge auth for `depfresh update`, or default
values for CLI options.

## Precedence

Sources are merged lowest-to-highest:

```
built-in defaults  <  config file(s)  <  environment  <  CLI flags
```

So an environment variable overrides a config file, and a CLI flag overrides
both.

## Config file

JSON, auto-discovered (project files win over home files):

1. `~/.config/depfresh/config.json`
2. `~/.depfresh.json`
3. `<project>/depfresh.json`
4. `<project>/.depfresh.json`

Or point at one explicitly with `--config PATH`.

```jsonc
{
  "settings": {
    "check-updates": true,
    "ecosystem": ["python", "node"],
    "grouping": "ecosystem"
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
    },
    "java": { "base_url": "https://nexus.acme.com/repository/maven-public" }
  },
  "forges": {
    "github": { "token": "${GITHUB_TOKEN}" },
    "gitlab": { "base_url": "https://git.acme.com/api/v4", "kind": "gitlab" }
  }
}
```

`${VAR}` in any string value is expanded from the environment, keeping secrets
out of the file. Unknown keys under `settings` are rejected with a clear error.

### `settings`

Defaults for CLI options, so you don't repeat them. Field names mirror the flags
(dashes accepted, e.g. `check-updates`): `path`, `json`, `ecosystem`,
`manifests-only`, `flat`, `check-updates`, `outdated-only`, `bump-plan`,
`exit-code`, `timeout`, `jobs`, and the update options `grouping`,
`branch-prefix`, `base`, `exclude`, `dry-run`.

### `registries`

Per-ecosystem endpoint + auth. Fields: `base_url`, `token` (bearer),
`username` + `password` (basic auth), and free-form `headers`.

### `forges`

Per-forge auth for `depfresh update`. Keyed by forge kind (`github`, `gitlab`).
Fields: `token`, `base_url` (API base for self-hosted), and `kind` (only needed
when the host name doesn't contain "github"/"gitlab").

## Environment variables

`<ECO>` is the upper-cased ecosystem (e.g. `PYTHON`); `<KIND>` is `GITHUB` or
`GITLAB`.

| Variable | Purpose |
|----------|---------|
| `DEPFRESH_REGISTRY_<ECO>` | Registry base URL |
| `DEPFRESH_TOKEN_<ECO>` | Registry bearer token |
| `DEPFRESH_USERNAME_<ECO>` | Registry basic-auth user |
| `DEPFRESH_PASSWORD_<ECO>` | Registry basic-auth password |
| `DEPFRESH_FORGE_TOKEN_<KIND>` | Forge token for `depfresh update` |
| `DEPFRESH_FORGE_URL_<KIND>` | Forge API base URL (self-hosted) |

```console
export DEPFRESH_TOKEN_PYTHON="$PYPI_TOKEN"
export DEPFRESH_FORGE_TOKEN_GITHUB="$GITHUB_TOKEN"
depfresh --check-updates
```

## CLI overrides

For one-off runs, override registries without a file:

```console
depfresh --check-updates \
  --registry python=https://pypi.acme.com/simple \
  --registry-token python="$PYPI_TOKEN"
```

## Examples

### Private PyPI + npm mirror (Artifactory)

```jsonc
{
  "registries": {
    "python": { "base_url": "https://artifactory.acme.com/api/pypi/pypi/simple", "token": "${ART_TOKEN}" },
    "node":   { "base_url": "https://artifactory.acme.com/api/npm/npm",          "token": "${ART_TOKEN}" }
  }
}
```

### Self-hosted GitLab for updates

```jsonc
{
  "forges": {
    "gitlab": { "base_url": "https://git.acme.com/api/v4", "kind": "gitlab", "token": "${GL_TOKEN}" }
  }
}
```

```console
depfresh update https://git.acme.com/team/app
```
