"""Tests for registry configuration loading and merging."""

from __future__ import annotations

import base64
import json

import pytest

from depfresh.config import (
    ForgeConfig,
    RegistryConfig,
    from_env,
    from_json,
    load_config,
    merge,
)


def test_auth_headers_bearer():
    headers = RegistryConfig(token="abc").auth_headers()
    assert headers["Authorization"] == "Bearer abc"


def test_auth_headers_basic():
    headers = RegistryConfig(username="ci", password="pw").auth_headers()
    expected = "Basic " + base64.b64encode(b"ci:pw").decode()
    assert headers["Authorization"] == expected


def test_auth_headers_token_wins_over_basic():
    headers = RegistryConfig(token="t", username="ci", password="pw").auth_headers()
    assert headers["Authorization"] == "Bearer t"


def test_from_json_with_env_expansion(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "s3cret")
    text = json.dumps(
        {
            "registries": {
                "python": {"base_url": "https://pypi.acme.com", "token": "${MY_TOKEN}"},
                "java": {"base_url": "https://nexus.acme.com/repository/maven-public"},
            }
        }
    )
    config = from_json(text)
    assert config.registries["python"].base_url == "https://pypi.acme.com"
    assert config.registries["python"].token == "s3cret"
    assert "nexus.acme.com" in config.registries["java"].base_url


def test_from_json_rejects_non_object():
    with pytest.raises(ValueError):
        from_json("[1, 2, 3]")


def test_from_json_invalid_json():
    with pytest.raises(ValueError):
        from_json("{ not valid json ")


def test_from_env():
    env = {
        "DEPFRESH_REGISTRY_PYTHON": "https://pypi.acme.com",
        "DEPFRESH_TOKEN_PYTHON": "tok",
        "DEPFRESH_USERNAME_NODE": "ci",
        "DEPFRESH_PASSWORD_NODE": "pw",
        "UNRELATED": "ignored",
    }
    config = from_env(env)
    assert config.registries["python"].base_url == "https://pypi.acme.com"
    assert config.registries["python"].token == "tok"
    assert config.registries["node"].username == "ci"
    assert config.registries["node"].password == "pw"
    assert "unrelated" not in config.registries


def test_merge_precedence():
    base = from_json(
        json.dumps({"registries": {"python": {"base_url": "https://a", "token": "file-token"}}})
    )
    override = from_env({"DEPFRESH_REGISTRY_PYTHON": "https://b"})
    result = merge(base, override)
    # later config overrides base_url but keeps the file's token (not re-set)
    assert result.registries["python"].base_url == "https://b"
    assert result.registries["python"].token == "file-token"


def _write_config(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_config_explicit_path(tmp_path, monkeypatch):
    monkeypatch.delenv("DEPFRESH_REGISTRY_PYTHON", raising=False)
    cfg_file = tmp_path / "depfresh.json"
    _write_config(cfg_file, {"registries": {"python": {"base_url": "https://pypi.acme.com"}}})
    config = load_config(explicit_path=cfg_file, environ={})
    assert config.registries["python"].base_url == "https://pypi.acme.com"


def test_load_config_missing_explicit_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(explicit_path=tmp_path / "nope.json", environ={})


def test_load_config_autodiscovers_project_file(tmp_path):
    _write_config(
        tmp_path / "depfresh.json", {"registries": {"node": {"base_url": "https://npm.acme.com"}}}
    )
    config = load_config(scan_path=tmp_path, environ={})
    assert config.registries["node"].base_url == "https://npm.acme.com"


def test_from_json_parses_settings():
    text = json.dumps(
        {
            "settings": {
                "check-updates": True,
                "json": True,
                "timeout": 15.0,
                "jobs": 24,
                "ecosystem": ["python", "node"],
            }
        }
    )
    config = from_json(text)
    assert config.settings.check_updates is True
    assert config.settings.json is True
    assert config.settings.timeout == 15.0
    assert config.settings.jobs == 24
    assert config.settings.ecosystem == ["python", "node"]


def test_from_json_rejects_unknown_setting():
    with pytest.raises(ValueError):
        from_json(json.dumps({"settings": {"nope": True}}))


def test_settings_merge_precedence():
    base = from_json(json.dumps({"settings": {"json": True, "timeout": 5.0}}))
    override = from_json(json.dumps({"settings": {"timeout": 30.0}}))
    result = merge(base, override)
    assert result.settings.json is True  # kept from base
    assert result.settings.timeout == 30.0  # overridden


def test_load_config_env_overrides_file(tmp_path):
    _write_config(
        tmp_path / "depfresh.json", {"registries": {"node": {"base_url": "https://from-file"}}}
    )
    config = load_config(scan_path=tmp_path, environ={"DEPFRESH_REGISTRY_NODE": "https://from-env"})
    assert config.registries["node"].base_url == "https://from-env"


def test_from_json_parses_forges(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ghp_xyz")
    config = from_json(
        json.dumps(
            {
                "forges": {
                    "github": {"token": "${GH_TOKEN}"},
                    "gitlab": {"base_url": "https://git.acme.com/api/v4", "kind": "gitlab"},
                }
            }
        )
    )
    assert config.forges["github"].token == "ghp_xyz"
    assert config.forges["gitlab"].base_url == "https://git.acme.com/api/v4"
    assert config.forges["gitlab"].kind == "gitlab"


def test_from_env_parses_forge_token():
    config = from_env(
        {"DEPFRESH_FORGE_TOKEN_GITHUB": "tok", "DEPFRESH_FORGE_URL_GITLAB": "https://g/api/v4"}
    )
    assert config.forges["github"].token == "tok"
    assert config.forges["gitlab"].base_url == "https://g/api/v4"


def test_merge_forge_precedence():
    base = from_json(json.dumps({"forges": {"github": {"token": "filetok", "kind": "github"}}}))
    override = from_env({"DEPFRESH_FORGE_TOKEN_GITHUB": "envtok"})
    result = merge(base, override)
    assert result.forges["github"].token == "envtok"  # env overrides
    assert result.forges["github"].kind == "github"  # kept from file
    assert result.for_forge("GitHub").token == "envtok"  # case-insensitive lookup


def test_forge_config_merged_keeps_unset():
    merged = ForgeConfig(token="a", kind="github").merged(ForgeConfig(base_url="https://x"))
    assert merged == ForgeConfig(token="a", base_url="https://x", kind="github")


def test_from_json_parses_update_settings():
    config = from_json(
        json.dumps(
            {
                "settings": {
                    "grouping": "ecosystem",
                    "branch-prefix": "bot/",
                    "exclude": ["left-pad"],
                    "dry-run": True,
                }
            }
        )
    )
    assert config.settings.grouping == "ecosystem"
    assert config.settings.branch_prefix == "bot/"
    assert config.settings.exclude == ["left-pad"]
    assert config.settings.dry_run is True
