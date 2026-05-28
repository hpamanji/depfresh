# Extending depfresh

Adding support for a new manifest format or ecosystem is intentionally small.
There are four extension points; you rarely need all of them.

| To… | Add a… | In | Registered in |
|-----|--------|----|---------------|
| Read a new manifest | `Parser` | `parsers/<eco>.py` | `parsers/registry.py` (`PARSERS`) |
| Check updates for an ecosystem | `Registry` | `resolver.py` | `_REGISTRIES` |
| Let `update` rewrite a manifest | `Editor` | `editors/<eco>.py` | `editors/registry.py` (`EDITORS`) |
| Support a new git forge | `Forge` | `forge/<name>.py` | `forge/detect.py` |

Install the dev extra first (`pip install -e ".[dev]"`) and run `pytest` as you
go.

## Add a parser

```python
# src/depfresh/parsers/elixir.py
from depfresh.models import Dependency
from depfresh.parsers.base import Parser

class MixExsParser(Parser):
    ecosystem = "elixir"
    manager = "mix"
    filenames = ("mix.exs",)        # exact basenames
    # patterns = ("*.foo",)          # or fnmatch globs

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        # ... locate dependencies in `text` ...
        deps.append(self._dep("phoenix", "~> 1.7", scope="runtime"))
        return deps
```

Use `self._dep(name, version, scope=...)` — it trims whitespace and normalizes
empty versions to `None`. Then add an instance to `PARSERS` in
`parsers/registry.py` and a test in `tests/test_parsers.py`.

## Add a registry (update checks)

```python
# in src/depfresh/resolver.py
class HexRegistry(Registry):
    ecosystem = "elixir"
    default_base_url = "https://hex.pm/api/packages"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{name}"
        data = json.loads(fetch(url, config.auth_headers()))
        return data.get("latest_stable_version")
```

Add it to the `_REGISTRIES` map and test it in `tests/test_resolver.py` with the
`recording_fetch` helper (no real network). Using `config.base_url` /
`config.auth_headers()` keeps private registries and auth working for free.

## Add an editor (for `depfresh update`)

Editors do **text-level** replacement so comments/formatting survive — never
parse-and-reserialize. Reuse a helper from `editors/base.py`:

```python
# src/depfresh/editors/elixir.py
from depfresh.editors.base import EditResult, Editor, replace_toml_dependency

class MixExsEditor(Editor):
    ecosystem = "elixir"
    filenames = ("mix.exs",)

    def apply(self, text, name, current, latest) -> EditResult:
        return replace_toml_dependency(text, name, latest)   # (new_text, changed)
```

Available helpers: `replace_json_dependency`, `replace_toml_dependency`,
`replace_requirements_dependency`, `replace_pom_dependency`,
`replace_coordinate_dependency`, `replace_dotnet_dependency`,
`replace_gomod_dependency`, `replace_gemfile_dependency`. New versions are
computed by `versioning.bump_constraint`, which preserves the operator/prefix.

Add the editor to `EDITORS` in `editors/registry.py` (declared manifests only —
**not** lockfiles) and test it in `tests/test_editors.py`, asserting formatting
is preserved and the result re-parses to the new version.

## Add a forge

Implement the `Forge` interface (`forge/base.py`): `default_branch`,
`open_request`, `existing_request`, and a `_default_api(host)`. Model it on
`forge/github.py` / `forge/gitlab.py`, wire host detection into
`forge/detect.py`, and test with a canned `request` callable in
`tests/test_forge.py`.

## Checklist before a PR

- [ ] Tests added/updated; `pytest` green.
- [ ] No third-party runtime dependency introduced.
- [ ] `ruff check`, `ruff format --check`, `mypy src/depfresh` pass.
- [ ] Docs updated if behaviour or options changed.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full workflow and coding style.
