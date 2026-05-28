"""Tests for registry resolution and outdated detection (no real network)."""

from __future__ import annotations

import json
import urllib.error

from depfresh.config import DepfreshConfig, RegistryConfig
from depfresh.models import Dependency, ManifestResult, ScanResult
from depfresh.resolver import (
    CURRENT,
    ERROR,
    NOT_FOUND,
    OUTDATED,
    UNKNOWN,
    CratesRegistry,
    GoRegistry,
    MavenRegistry,
    NpmRegistry,
    NuGetRegistry,
    PackagistRegistry,
    PyPIRegistry,
    RubyGemsRegistry,
    _go_escape,
    check_updates,
)

NO_CONFIG = RegistryConfig()


def recording_fetch(responses):
    """Return (fetch, calls). fetch(url, headers) matches a URL substring.

    Dict responses are JSON-encoded; string responses (e.g. XML) pass through.
    ``calls`` records (url, headers) tuples.
    """
    calls: list[tuple[str, dict]] = []

    def fetch(url, headers=None):
        calls.append((url, headers or {}))
        for key, value in responses.items():
            if key in url:
                return value if isinstance(value, str) else json.dumps(value)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    return fetch, calls


def test_pypi_registry():
    fetch, calls = recording_fetch({"pypi.org/pypi/requests": {"info": {"version": "2.31.0"}}})
    assert PyPIRegistry().latest("requests", fetch, NO_CONFIG) == "2.31.0"
    assert "pypi.org/pypi/requests/json" in calls[0][0]


def test_pypi_registry_with_private_base_and_token():
    fetch, calls = recording_fetch({"pypi.acme.com": {"info": {"version": "9.9.9"}}})
    config = RegistryConfig(base_url="https://pypi.acme.com/simple-json", token="secret")
    assert PyPIRegistry().latest("internal-pkg", fetch, config) == "9.9.9"
    url, headers = calls[0]
    assert url == "https://pypi.acme.com/simple-json/internal-pkg/json"
    assert headers["Authorization"] == "Bearer secret"


def test_npm_registry_scoped():
    fetch, calls = recording_fetch(
        {"registry.npmjs.org/@types/node": {"dist-tags": {"latest": "20.0.0"}}}
    )
    assert NpmRegistry().latest("@types/node", fetch, NO_CONFIG) == "20.0.0"
    assert "@types/node" in calls[0][0]  # scope slash preserved


def test_crates_registry():
    fetch, _ = recording_fetch({"crates.io": {"crate": {"max_stable_version": "1.0.140"}}})
    assert CratesRegistry().latest("serde", fetch, NO_CONFIG) == "1.0.140"


def test_go_registry_escapes_uppercase():
    fetch, calls = recording_fetch({"proxy.golang.org": {"Version": "v1.2.0"}})
    assert GoRegistry().latest("github.com/Foo/Bar", fetch, NO_CONFIG) == "v1.2.0"
    assert "github.com/!foo/!bar/@latest" in calls[0][0]


def test_go_escape():
    assert _go_escape("github.com/Foo/Bar") == "github.com/!foo/!bar"
    assert _go_escape("golang.org/x/sys") == "golang.org/x/sys"


def test_maven_registry_public_search():
    fetch, calls = recording_fetch(
        {"search.maven.org": {"response": {"docs": [{"latestVersion": "6.1.0"}]}}}
    )
    assert MavenRegistry().latest("org.springframework:spring-core", fetch, NO_CONFIG) == "6.1.0"
    assert "solrsearch" in calls[0][0]


def test_maven_registry_private_uses_metadata_xml():
    metadata = """<?xml version="1.0"?>
<metadata>
  <groupId>com.acme</groupId>
  <artifactId>widget</artifactId>
  <versioning>
    <release>3.4.0</release>
    <versions><version>3.3.0</version><version>3.4.0</version></versions>
  </versioning>
</metadata>
"""
    fetch, calls = recording_fetch({"nexus.acme.com": metadata})
    config = RegistryConfig(base_url="https://nexus.acme.com/repository/maven-public")
    assert MavenRegistry().latest("com.acme:widget", fetch, config) == "3.4.0"
    assert "com/acme/widget/maven-metadata.xml" in calls[0][0]


def test_maven_registry_requires_coordinate():
    fetch, _ = recording_fetch({})
    assert MavenRegistry().latest("no-colon-name", fetch, NO_CONFIG) is None


def test_rubygems_registry():
    fetch, _ = recording_fetch({"rubygems.org": {"version": "7.1.0"}})
    assert RubyGemsRegistry().latest("rails", fetch, NO_CONFIG) == "7.1.0"


def test_packagist_skips_dev_versions():
    fetch, _ = recording_fetch(
        {
            "repo.packagist.org": {
                "packages": {"monolog/monolog": [{"version": "dev-main"}, {"version": "3.5.0"}]}
            }
        }
    )
    assert PackagistRegistry().latest("monolog/monolog", fetch, NO_CONFIG) == "3.5.0"


def test_nuget_prefers_stable():
    fetch, calls = recording_fetch(
        {"api.nuget.org": {"versions": ["1.0.0", "2.0.0-beta", "2.0.0"]}}
    )
    assert NuGetRegistry().latest("Newtonsoft.Json", fetch, NO_CONFIG) == "2.0.0"
    assert "newtonsoft.json" in calls[0][0]  # id lower-cased


def _sample_result():
    return ScanResult(
        root="proj",
        manifests=[
            ManifestResult(
                path="requirements.txt",
                ecosystem="python",
                manager="pip",
                dependencies=[
                    Dependency("requests", "==2.0.0", "python"),
                    Dependency("flask", None, "python"),  # no pinnable version
                ],
            ),
            ManifestResult(
                path="package.json",
                ecosystem="node",
                manager="npm",
                dependencies=[Dependency("react", "^18.2.0", "node")],
            ),
            ManifestResult(
                path="go.mod",
                ecosystem="go",
                manager="go",
                dependencies=[Dependency("github.com/x/y", "v9.9.9", "go")],
            ),
        ],
    )


def test_check_updates_statuses():
    responses = {
        "pypi.org/pypi/requests": {"info": {"version": "2.31.0"}},
        "pypi.org/pypi/flask": {"info": {"version": "3.0.0"}},
        "registry.npmjs.org/react": {"dist-tags": {"latest": "18.2.0"}},
        # go.mod dep deliberately absent -> 404 -> not found
    }
    fetch, _ = recording_fetch(responses)
    updates = check_updates(_sample_result(), fetch=fetch, max_workers=4)

    assert updates[("python", "requests")].status == OUTDATED
    assert updates[("python", "requests")].latest == "2.31.0"
    assert updates[("node", "react")].status == CURRENT
    assert updates[("python", "flask")].status == UNKNOWN  # latest known, no current
    assert updates[("go", "github.com/x/y")].status == NOT_FOUND


def test_check_updates_uses_config_base_url():
    fetch, calls = recording_fetch({"pypi.acme.com": {"info": {"version": "2.31.0"}}})
    config = DepfreshConfig(
        registries={"python": RegistryConfig(base_url="https://pypi.acme.com/pypi")}
    )
    result = ScanResult(
        root="x",
        manifests=[
            ManifestResult(
                path="requirements.txt",
                ecosystem="python",
                manager="pip",
                dependencies=[Dependency("requests", "==2.0.0", "python")],
            )
        ],
    )
    updates = check_updates(result, config=config, fetch=fetch, max_workers=1)
    assert updates[("python", "requests")].status == OUTDATED
    assert calls[0][0].startswith("https://pypi.acme.com/pypi/")


def test_check_updates_records_errors():
    def fetch(url, headers=None):
        raise urllib.error.URLError("connection refused")

    updates = check_updates(_sample_result(), fetch=fetch, max_workers=2)
    assert all(i.status == ERROR for i in updates.values())


def test_check_updates_skips_unknown_ecosystem():
    result = ScanResult(
        root="x",
        manifests=[
            ManifestResult(
                path="weird.toml",
                ecosystem="haskell",
                manager="cabal",
                dependencies=[Dependency("text", "1.0", "haskell")],
            )
        ],
    )
    fetch, calls = recording_fetch({})
    updates = check_updates(result, fetch=fetch)
    assert updates == {}
    assert calls == []  # no registry, nothing fetched
