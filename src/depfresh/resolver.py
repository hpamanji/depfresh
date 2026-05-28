"""Resolve the latest available version of dependencies from registries.

Network access is performed here and nowhere else; the base scan stays offline.
Registries default to public endpoints but every base URL and the auth used to
reach it is configurable (see :mod:`depfresh.config`) so private/org registries
work too. Lookups are deduplicated per ``(ecosystem, name)`` and run in
parallel. All fetching goes through an injectable ``fetch`` callable so the
logic is testable without touching the network.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from xml.etree import ElementTree as ET

from depfresh.config import DepfreshConfig, RegistryConfig
from depfresh.models import ScanResult
from depfresh.versioning import extract_current_version, is_outdated

# Statuses for an update check.
OUTDATED = "outdated"
CURRENT = "current"
UNKNOWN = "unknown"  # registry reachable but no comparable version determined
NOT_FOUND = "not_found"  # package not in registry
ERROR = "error"  # network/parse failure


@dataclass
class UpdateInfo:
    ecosystem: str
    name: str
    current: str | None  # constraint as written in the manifest
    current_version: str | None  # comparable version extracted from the constraint
    latest: str | None
    status: str
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Registry clients                                                            #
# --------------------------------------------------------------------------- #


class Registry:
    """Maps a package name to its latest version for one ecosystem.

    ``fetch`` is ``fetch(url, headers) -> str`` returning the response body.
    ``config`` supplies the base-URL override and auth headers for this lookup.
    """

    ecosystem: str = ""
    default_base_url: str = ""

    def base(self, config: RegistryConfig) -> str:
        return (config.base_url or self.default_base_url).rstrip("/")

    def latest(self, name: str, fetch, config: RegistryConfig) -> str | None:  # pragma: no cover
        raise NotImplementedError


class PyPIRegistry(Registry):
    ecosystem = "python"
    default_base_url = "https://pypi.org/pypi"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{urllib.parse.quote(name)}/json"
        data = json.loads(fetch(url, config.auth_headers()))
        return data.get("info", {}).get("version")


class NpmRegistry(Registry):
    ecosystem = "node"
    default_base_url = "https://registry.npmjs.org"

    def latest(self, name, fetch, config):
        # Keep '@' and '/' so scoped packages (@scope/pkg) resolve correctly.
        url = f"{self.base(config)}/{urllib.parse.quote(name, safe='@/')}"
        data = json.loads(fetch(url, config.auth_headers()))
        return (data.get("dist-tags") or {}).get("latest")


class CratesRegistry(Registry):
    ecosystem = "rust"
    default_base_url = "https://crates.io/api/v1/crates"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{urllib.parse.quote(name)}"
        crate = json.loads(fetch(url, config.auth_headers())).get("crate", {})
        return crate.get("max_stable_version") or crate.get("newest_version")


class GoRegistry(Registry):
    ecosystem = "go"
    default_base_url = "https://proxy.golang.org"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{_go_escape(name)}/@latest"
        return json.loads(fetch(url, config.auth_headers())).get("Version")


class MavenRegistry(Registry):
    ecosystem = "java"
    default_base_url = "https://search.maven.org/solrsearch/select"

    def latest(self, name, fetch, config):
        if ":" not in name:
            return None
        group, artifact = name.split(":", 1)
        # A configured base_url is a real Maven repo (Nexus/Artifactory): read
        # the standard maven-metadata.xml. Only the public default supports the
        # Central search API.
        if config.base_url:
            path = group.replace(".", "/")
            url = f"{self.base(config)}/{path}/{artifact}/maven-metadata.xml"
            return _parse_maven_metadata(fetch(url, config.auth_headers()))
        query = urllib.parse.urlencode(
            {"q": f'g:"{group}" AND a:"{artifact}"', "rows": "1", "wt": "json"}
        )
        data = json.loads(fetch(f"{self.default_base_url}?{query}", config.auth_headers()))
        docs = (data.get("response") or {}).get("docs") or []
        if not docs:
            return None
        return docs[0].get("latestVersion") or docs[0].get("v")


class RubyGemsRegistry(Registry):
    ecosystem = "ruby"
    default_base_url = "https://rubygems.org/api/v1/gems"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{urllib.parse.quote(name)}.json"
        return json.loads(fetch(url, config.auth_headers())).get("version")


class PackagistRegistry(Registry):
    ecosystem = "php"
    default_base_url = "https://repo.packagist.org/p2"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{name}.json"
        data = json.loads(fetch(url, config.auth_headers()))
        versions = (data.get("packages") or {}).get(name) or []
        for entry in versions:  # newest first
            version = entry.get("version", "")
            if version and "dev" not in version.lower():
                return version.lstrip("vV")
        return versions[0].get("version") if versions else None


class NuGetRegistry(Registry):
    ecosystem = "dotnet"
    default_base_url = "https://api.nuget.org/v3-flatcontainer"

    def latest(self, name, fetch, config):
        url = f"{self.base(config)}/{name.lower()}/index.json"
        versions = json.loads(fetch(url, config.auth_headers())).get("versions") or []
        stable = [v for v in versions if "-" not in v]
        if stable:
            return stable[-1]
        return versions[-1] if versions else None


def _go_escape(module: str) -> str:
    """Go module proxy lower-cases via '!' escaping: 'Foo' -> '!foo'."""
    return "".join(f"!{c.lower()}" if c.isupper() else c for c in module)


def _parse_maven_metadata(text: str) -> str | None:
    """Pull the newest version out of a maven-metadata.xml document."""
    root = ET.fromstring(text)
    versioning = root.find("versioning")
    if versioning is None:
        return None
    for tag in ("release", "latest"):
        node = versioning.find(tag)
        if node is not None and node.text:
            return node.text.strip()
    versions = [v.text.strip() for v in versioning.findall("versions/version") if v.text]
    return versions[-1] if versions else None


_REGISTRIES: dict[str, Registry] = {
    r.ecosystem: r
    for r in (
        PyPIRegistry(),
        NpmRegistry(),
        CratesRegistry(),
        GoRegistry(),
        MavenRegistry(),
        RubyGemsRegistry(),
        PackagistRegistry(),
        NuGetRegistry(),
    )
}


def supported_ecosystems() -> list[str]:
    return sorted(_REGISTRIES)


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #


def make_default_fetch(timeout: float = 10.0):
    """Build an HTTP fetcher (returns the response body as text)."""

    def fetch(url: str, headers: dict[str, str] | None = None) -> str:
        request_headers = {
            "User-Agent": "depfresh (+https://github.com/hpamanji/depfresh)",
            "Accept": "*/*",
        }
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")

    return fetch


def _resolve_one(
    ecosystem: str, name: str, constraint: str | None, fetch, reg_config: RegistryConfig
) -> UpdateInfo:
    registry = _REGISTRIES[ecosystem]
    current_version = extract_current_version(constraint)
    try:
        latest = registry.latest(name, fetch, reg_config)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateInfo(ecosystem, name, constraint, current_version, None, NOT_FOUND)
        return UpdateInfo(
            ecosystem, name, constraint, current_version, None, ERROR, f"HTTP {exc.code}"
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure per dependency
        return UpdateInfo(
            ecosystem, name, constraint, current_version, None, ERROR, str(exc)
        )

    if latest is None:
        return UpdateInfo(ecosystem, name, constraint, current_version, None, NOT_FOUND)
    if current_version is None:
        # We know the latest, but the constraint had no pinnable version
        # (wildcard, URL, or centrally managed) so we can't judge staleness.
        return UpdateInfo(ecosystem, name, constraint, current_version, latest, UNKNOWN)

    status = OUTDATED if is_outdated(current_version, latest) else CURRENT
    return UpdateInfo(ecosystem, name, constraint, current_version, latest, status)


def check_updates(
    result: ScanResult,
    *,
    config: DepfreshConfig | None = None,
    fetch=None,
    max_workers: int = 16,
    timeout: float = 10.0,
) -> dict[tuple[str, str], UpdateInfo]:
    """Resolve latest versions for every dependency in ``result``.

    Returns a mapping keyed by ``(ecosystem, name)``. Only ecosystems with a
    known registry are queried; others are skipped silently. Pass ``config`` to
    target private registries / supply authentication.
    """
    if config is None:
        config = DepfreshConfig()
    if fetch is None:
        fetch = make_default_fetch(timeout)

    # Deduplicate to one lookup per (ecosystem, name), keeping the first
    # constraint we saw as the representative for comparison.
    targets: dict[tuple[str, str], str | None] = {}
    for manifest in result.manifests:
        for dep in manifest.dependencies:
            if dep.ecosystem not in _REGISTRIES:
                continue
            targets.setdefault((dep.ecosystem, dep.name), dep.version)

    results: dict[tuple[str, str], UpdateInfo] = {}
    if not targets:
        return results

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {
            executor.submit(
                _resolve_one, ecosystem, name, constraint, fetch, config.for_ecosystem(ecosystem)
            ): (ecosystem, name)
            for (ecosystem, name), constraint in targets.items()
        }
        for future in as_completed(futures):
            info = future.result()
            results[(info.ecosystem, info.name)] = info

    return results
