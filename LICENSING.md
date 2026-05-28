# Licensing

depfresh is an **open-core** project. Licensing is **per package**, not per repo:

| Package | Path | License |
|---------|------|---------|
| `depfresh` (core) | [`packages/depfresh`](packages/depfresh) | **MIT** ([LICENSE](packages/depfresh/LICENSE)) |
| `depfresh-pro` | [`packages/depfresh-pro`](packages/depfresh-pro) | **AGPL-3.0-or-later OR commercial** ([LICENSE](packages/depfresh-pro/LICENSE), [COMMERCIAL.md](packages/depfresh-pro/COMMERCIAL.md)) |

The repository's top-level `LICENSE` is MIT and applies to the **core**. The
`depfresh-pro` directory carries its own AGPL license and a commercial option.

## Dependency direction (important)

The pro layer **depends on** the core; the **core never depends on the pro
layer**. This keeps the MIT core free of any AGPL "reach-back": the core is fully
functional and shippable on its own, and `depfresh update` only exists when the
separately-licensed `depfresh-pro` package is installed (discovered at runtime
via the `depfresh.commands` entry-point group — no import from core to pro).

## Dual licensing of `depfresh-pro`

`depfresh-pro` is offered under **AGPL-3.0-or-later OR a commercial license**, at
the user's choice. AGPL is the free option; organizations that can't accept its
copyleft/network-disclosure terms can buy a commercial license
(see [COMMERCIAL.md](packages/depfresh-pro/COMMERCIAL.md)).

## Contributions

To keep the dual-licensing option viable, contributions to `depfresh-pro` require
agreeing to the [Contributor License Agreement](CLA.md). See
[CONTRIBUTING.md](CONTRIBUTING.md).

> This is a summary, not legal advice.
