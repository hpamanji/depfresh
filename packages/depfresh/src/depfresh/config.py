"""Configuration for registry endpoints and authentication.

Lets depfresh target private/internal registries (Artifactory, Nexus, Azure
Artifacts, devpi, Verdaccio, ...) instead of the public defaults. Config is
merged from several sources, lowest precedence first:

    built-in defaults  <  config file(s)  <  environment  <  CLI flags

Config file (JSON), e.g. ``depfresh.json`` in the project or ``~/.depfresh.json``::

    {
      "settings": {
        "check-updates": true,
        "ecosystem": ["python", "node"]
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
        "java": {
          "base_url": "https://nexus.acme.com/repository/maven-public"
        }
      }
    }

``${VAR}`` in any string value is expanded from the environment, keeping
secrets out of the file.

Environment variables (``<ECO>`` is the upper-cased ecosystem, e.g. PYTHON)::

    DEPFRESH_REGISTRY_<ECO>  base URL
    DEPFRESH_TOKEN_<ECO>     bearer token
    DEPFRESH_USERNAME_<ECO>  basic-auth user
    DEPFRESH_PASSWORD_<ECO>  basic-auth password
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

_ENV_FIELDS = {
    "DEPFRESH_REGISTRY_": "base_url",
    "DEPFRESH_TOKEN_": "token",
    "DEPFRESH_USERNAME_": "username",
    "DEPFRESH_PASSWORD_": "password",
}

# Forge auth, keyed by forge kind, e.g. DEPFRESH_FORGE_TOKEN_GITHUB.
_FORGE_ENV_FIELDS = {
    "DEPFRESH_FORGE_TOKEN_": "token",
    "DEPFRESH_FORGE_URL_": "base_url",
}


def _expand(value):
    """Expand ${VAR} / $VAR (and %VAR% on Windows) in string config values."""
    return os.path.expandvars(value) if isinstance(value, str) else value


@dataclass
class RegistryConfig:
    """Endpoint + auth overrides for a single ecosystem."""

    base_url: str | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def auth_headers(self) -> dict[str, str]:
        """Build request headers, deriving Authorization from token/basic auth."""
        out = dict(self.headers)
        if self.token:
            out.setdefault("Authorization", f"Bearer {self.token}")
        elif self.username is not None and self.password is not None:
            raw = f"{self.username}:{self.password}".encode()
            out.setdefault("Authorization", "Basic " + base64.b64encode(raw).decode())
        return out

    def merged(self, other: RegistryConfig) -> RegistryConfig:
        """Return a copy with ``other``'s set fields overriding this one's."""
        return RegistryConfig(
            base_url=other.base_url or self.base_url,
            token=other.token or self.token,
            username=other.username or self.username,
            password=other.password or self.password,
            headers={**self.headers, **other.headers},
        )


@dataclass
class ForgeConfig:
    """Auth + endpoint overrides for a git forge (used by ``depfresh update``)."""

    token: str | None = None
    base_url: str | None = None  # API base override for self-hosted instances
    kind: str | None = None  # "github" | "gitlab" — required for self-hosted hosts

    def merged(self, other: ForgeConfig) -> ForgeConfig:
        return ForgeConfig(
            token=other.token or self.token,
            base_url=other.base_url or self.base_url,
            kind=other.kind or self.kind,
        )


@dataclass
class Settings:
    """Default values for CLI options, so they need not be passed every run.

    Every field is optional; ``None`` means "not set here" so it can be
    overridden by a higher-precedence source. Field names mirror the CLI flags
    (dashes accepted in the config file, e.g. ``check-updates``).
    """

    path: str | None = None
    json: bool | None = None
    ecosystem: list[str] | None = None
    manifests_only: bool | None = None
    flat: bool | None = None
    check_updates: bool | None = None
    outdated_only: bool | None = None
    bump_plan: bool | None = None
    exit_code: bool | None = None
    timeout: float | None = None
    jobs: int | None = None
    # `depfresh update` options
    grouping: str | None = None  # all | ecosystem | dependency
    branch_prefix: str | None = None
    base: str | None = None  # override the target/default branch
    exclude: list[str] | None = None  # package names to skip
    dry_run: bool | None = None
    delete_branch: bool | None = None  # delete update branches once merged

    def merged(self, other: Settings) -> Settings:
        def pick(a, b):
            return b if b is not None else a

        return Settings(
            path=pick(self.path, other.path),
            json=pick(self.json, other.json),
            ecosystem=pick(self.ecosystem, other.ecosystem),
            manifests_only=pick(self.manifests_only, other.manifests_only),
            flat=pick(self.flat, other.flat),
            check_updates=pick(self.check_updates, other.check_updates),
            outdated_only=pick(self.outdated_only, other.outdated_only),
            bump_plan=pick(self.bump_plan, other.bump_plan),
            exit_code=pick(self.exit_code, other.exit_code),
            timeout=pick(self.timeout, other.timeout),
            jobs=pick(self.jobs, other.jobs),
            grouping=pick(self.grouping, other.grouping),
            branch_prefix=pick(self.branch_prefix, other.branch_prefix),
            base=pick(self.base, other.base),
            exclude=pick(self.exclude, other.exclude),
            dry_run=pick(self.dry_run, other.dry_run),
            delete_branch=pick(self.delete_branch, other.delete_branch),
        )


_SETTINGS_FIELDS = {f for f in Settings.__dataclass_fields__}


@dataclass
class DepfreshConfig:
    registries: dict[str, RegistryConfig] = field(default_factory=dict)
    forges: dict[str, ForgeConfig] = field(default_factory=dict)
    settings: Settings = field(default_factory=Settings)

    def for_ecosystem(self, ecosystem: str) -> RegistryConfig:
        return self.registries.get(ecosystem, RegistryConfig())

    def for_forge(self, kind: str) -> ForgeConfig:
        return self.forges.get(kind.lower(), ForgeConfig())


def from_json(text: str) -> DepfreshConfig:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("config root must be a JSON object")
    config = DepfreshConfig()
    for ecosystem, raw in (data.get("registries") or {}).items():
        config.registries[ecosystem.lower()] = RegistryConfig(
            base_url=_expand(raw.get("base_url")),
            token=_expand(raw.get("token")),
            username=_expand(raw.get("username")),
            password=_expand(raw.get("password")),
            headers={k: _expand(v) for k, v in (raw.get("headers") or {}).items()},
        )

    for kind, raw in (data.get("forges") or {}).items():
        config.forges[kind.lower()] = ForgeConfig(
            token=_expand(raw.get("token")),
            base_url=_expand(raw.get("base_url")),
            kind=raw.get("kind"),
        )

    # Accept both "check-updates" and "check_updates" spellings.
    raw_settings = {k.replace("-", "_"): v for k, v in (data.get("settings") or {}).items()}
    unknown = set(raw_settings) - _SETTINGS_FIELDS
    if unknown:
        raise ValueError(f"unknown setting(s): {', '.join(sorted(unknown))}")
    config.settings = Settings(**{k: v for k, v in raw_settings.items() if k in _SETTINGS_FIELDS})
    return config


def from_env(environ: Mapping[str, str]) -> DepfreshConfig:
    config = DepfreshConfig()
    for key, value in environ.items():
        for prefix, field_name in _ENV_FIELDS.items():
            if key.startswith(prefix):
                ecosystem = key[len(prefix) :].lower()
                if ecosystem:
                    reg = config.registries.setdefault(ecosystem, RegistryConfig())
                    setattr(reg, field_name, value)
        for prefix, field_name in _FORGE_ENV_FIELDS.items():
            if key.startswith(prefix):
                kind = key[len(prefix) :].lower()
                if kind:
                    forge = config.forges.setdefault(kind, ForgeConfig())
                    setattr(forge, field_name, value)
    return config


def merge(*configs: DepfreshConfig) -> DepfreshConfig:
    """Merge configs left-to-right; later configs override earlier ones."""
    out = DepfreshConfig()
    for config in configs:
        for ecosystem, reg in config.registries.items():
            existing = out.registries.get(ecosystem, RegistryConfig())
            out.registries[ecosystem] = existing.merged(reg)
        for kind, forge in config.forges.items():
            existing_forge = out.forges.get(kind, ForgeConfig())
            out.forges[kind] = existing_forge.merged(forge)
        out.settings = out.settings.merged(config.settings)
    return out


def _candidate_paths(scan_path: str | os.PathLike[str] | None) -> list[Path]:
    home = Path.home()
    paths = [home / ".config" / "depfresh" / "config.json", home / ".depfresh.json"]
    root = Path(scan_path) if scan_path else Path.cwd()
    if root.is_file():
        root = root.parent
    # Project-local files take precedence over home, so list them last.
    paths += [root / "depfresh.json", root / ".depfresh.json"]
    return paths


def _read_config_file(path: Path) -> DepfreshConfig:
    try:
        return from_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:  # JSONDecodeError and our own validation errors
        raise ValueError(f"invalid config file {path}: {exc}") from exc


def load_config(
    *,
    explicit_path: str | os.PathLike[str] | None = None,
    scan_path: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> DepfreshConfig:
    """Load and merge config from file(s) and environment.

    If ``explicit_path`` is given, only that file is read (and must exist);
    otherwise the standard project/home locations are auto-discovered.
    Environment variables always override file values.
    """
    env: Mapping[str, str] = os.environ if environ is None else environ
    configs: list[DepfreshConfig] = []

    if explicit_path is not None:
        path = Path(explicit_path)
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        configs.append(_read_config_file(path))
    else:
        for path in _candidate_paths(scan_path):
            if path.is_file():
                configs.append(_read_config_file(path))

    configs.append(from_env(env))
    return merge(*configs)
