# depfresh documentation

depfresh is a dependency scanner that finds and parses dependency manifests
across many ecosystems, checks registries for newer versions, and can open
update PRs/MRs automatically.

These docs are modular — start with the [Quickstart](quickstart.md), then dive
into the guide for the task you have.

## Getting started

- [Installation](installation.md) — requirements and how to install.
- [Quickstart](quickstart.md) — the five things you'll do most, with examples.

## Guides

- [Scanning a project](scanning.md) — discover manifests and list dependencies
  (table / JSON / flat / manifests-only).
- [Checking for updates](checking-updates.md) — query registries, flag outdated
  deps, and build a bump plan.
- [Updating dependencies](updating.md) — `depfresh update`: clone, bump, push,
  and open a PR (GitHub) or MR (GitLab).
- [Configuration](configuration.md) — config files, environment variables,
  precedence, private registries, and forge auth.

## Reference

- [Supported ecosystems](ecosystems.md) — manifests, registries, and editors per
  ecosystem.
- [CLI reference](cli-reference.md) — every flag for `depfresh` and
  `depfresh update`.
- [Library API](library.md) — using depfresh from Python.

## Internals

- [Architecture](architecture.md) — how a run flows through the modules.
- [Extending depfresh](extending.md) — add a parser, registry, editor, or forge.

## See also

- Project [README](../README.md)
- [CONTRIBUTING](../CONTRIBUTING.md) and [Code of Conduct](../CODE_OF_CONDUCT.md)
