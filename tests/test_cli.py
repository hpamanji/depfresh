"""Tests for the CLI entry point."""

from __future__ import annotations

import json

from depfresh import cli
from depfresh.bump import build_bump_plan
from depfresh.cli import _render_bump_plan, main
from depfresh.models import Dependency, ManifestResult, ScanResult
from depfresh.resolver import CURRENT, OUTDATED, UpdateInfo


def _write(base, rel, content):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cli_table_output(tmp_path, capsys):
    _write(tmp_path, "requirements.txt", "requests==2.28.1\n")
    rc = main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "requests" in out
    assert "==2.28.1" in out


def test_cli_json_output(tmp_path, capsys):
    _write(tmp_path, "package.json", '{"dependencies": {"react": "^18.0.0"}}')
    rc = main([str(tmp_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["summary"]["dependency_count"] == 1
    assert payload["manifests"][0]["dependencies"][0]["name"] == "react"


def test_cli_ecosystem_filter(tmp_path, capsys):
    _write(tmp_path, "requirements.txt", "requests\n")
    _write(tmp_path, "package.json", '{"dependencies": {"react": "^18.0.0"}}')
    rc = main([str(tmp_path), "--json", "-e", "node"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["summary"]["manifest_count"] == 1
    assert payload["manifests"][0]["ecosystem"] == "node"


def test_cli_manifests_only_json(tmp_path, capsys):
    _write(tmp_path, "requirements.txt", "requests\nflask\n")
    rc = main([str(tmp_path), "--json", "--manifests-only"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "dependencies" not in payload["manifests"][0]


def test_cli_missing_path_returns_2(tmp_path, capsys):
    rc = main([str(tmp_path / "nope")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "error" in err


def test_cli_flat_table(tmp_path, capsys):
    _write(tmp_path, "svc/requirements.txt", "requests==2.0.0\n")
    _write(tmp_path, "web/package.json", '{"dependencies": {"react": "^18.0.0"}}')
    rc = main([str(tmp_path), "--flat"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "2 package record(s)" in out
    # each package line carries its source file
    for line in out.splitlines():
        if line.strip().startswith("requests"):
            assert "svc/requirements.txt" in line
        if line.strip().startswith("react"):
            assert "web/package.json" in line


def test_cli_flat_json(tmp_path, capsys):
    _write(tmp_path, "svc/requirements.txt", "requests==2.0.0\n")
    _write(tmp_path, "web/package.json", '{"dependencies": {"react": "^18.0.0"}}')
    rc = main([str(tmp_path), "--flat", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    by_name = {d["name"]: d for d in payload["dependencies"]}
    assert by_name["requests"]["manifest"] == "svc/requirements.txt"
    assert by_name["react"]["manifest"] == "web/package.json"


def _fake_updates(monkeypatch):
    """Stub check_updates so CLI tests never hit the network."""
    canned = {
        ("python", "requests"): UpdateInfo(
            "python", "requests", "==2.0.0", "2.0.0", "2.31.0", OUTDATED
        ),
        ("python", "flask"): UpdateInfo("python", "flask", "==3.0.0", "3.0.0", "3.0.0", CURRENT),
    }
    monkeypatch.setattr(cli, "check_updates", lambda result, **kw: canned)
    return canned


def test_cli_check_updates_table(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--check-updates"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OUTDATED" in out
    assert "2.31.0" in out
    assert "1 outdated" in out


def test_cli_check_updates_json(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--check-updates", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["summary"]["outdated_count"] == 1
    deps = {d["name"]: d for d in payload["manifests"][0]["dependencies"]}
    assert deps["requests"]["latest"] == "2.31.0"
    assert deps["requests"]["update_status"] == "outdated"


def test_cli_outdated_only_filters(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--outdated-only", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    names = [d["name"] for d in payload["manifests"][0]["dependencies"]]
    assert names == ["requests"]  # flask (up to date) filtered out


def test_cli_exit_code_on_outdated(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\n")
    rc = main([str(tmp_path), "--check-updates", "--exit-code"])
    capsys.readouterr()
    assert rc == 1


def test_cli_registry_override_passed_to_resolver(tmp_path, capsys, monkeypatch):
    captured = {}

    def spy(result, **kw):
        captured["config"] = kw.get("config")
        return {}

    monkeypatch.setattr(cli, "check_updates", spy)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\n")
    rc = main(
        [
            str(tmp_path),
            "--check-updates",
            "--registry",
            "python=https://pypi.acme.com",
            "--registry-token",
            "python=tok123",
        ]
    )
    capsys.readouterr()
    assert rc == 0
    python_cfg = captured["config"].registries["python"]
    assert python_cfg.base_url == "https://pypi.acme.com"
    assert python_cfg.token == "tok123"


def test_cli_bump_plan_table(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--bump-plan"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Bump plan: 1 package(s)" in out
    assert "requests  ->  2.31.0" in out
    assert "flask" not in out  # up to date, excluded


def test_cli_bump_plan_json(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--bump-plan", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    plan = payload["bump_plan"]
    assert plan["package_count"] == 1
    assert plan["items"][0]["name"] == "requests"
    assert plan["items"][0]["latest"] == "2.31.0"


def test_cli_settings_from_config_file(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    _write(tmp_path, "depfresh.json", '{"settings": {"check-updates": true, "json": true}}')
    rc = main([str(tmp_path)])  # no flags: behavior comes from the config file
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["summary"]["outdated_count"] == 1


def test_cli_flag_overrides_config_file(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\n")
    _write(tmp_path, "depfresh.json", '{"settings": {"json": true, "check-updates": true}}')
    rc = main([str(tmp_path), "--no-json"])  # CLI overrides config json=true
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("Scanned:")  # table, not JSON


def test_cli_exit_code_from_config(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\n")
    _write(tmp_path, "depfresh.json", '{"settings": {"check-updates": true, "exit-code": true}}')
    rc = main([str(tmp_path)])
    capsys.readouterr()
    assert rc == 1


def test_cli_flat_outdated_only_filters(tmp_path, capsys, monkeypatch):
    _fake_updates(monkeypatch)
    _write(tmp_path, "requirements.txt", "requests==2.0.0\nflask==3.0.0\n")
    rc = main([str(tmp_path), "--flat", "--outdated-only"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "requests" in out
    assert "flask" not in out  # up to date, filtered out even in flat view


def test_render_bump_plan_counts_distinct_files():
    # Same package declared twice in one file (different constraints) is still
    # one file in the header count.
    result = ScanResult(
        root="p",
        manifests=[
            ManifestResult(
                path="pyproject.toml",
                ecosystem="python",
                manager="pip",
                dependencies=[
                    Dependency("requests", ">=2.0", "python", scope="runtime"),
                    Dependency("requests", ">=2.28", "python", scope="optional"),
                ],
            )
        ],
    )
    updates = {
        ("python", "requests"): UpdateInfo("python", "requests", None, None, "2.31.0", OUTDATED)
    }
    out = _render_bump_plan("p", build_bump_plan(result, updates))
    assert "(1 file)" in out
    assert "(2 file" not in out


def test_cli_bad_registry_arg_returns_2(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(cli, "check_updates", lambda result, **kw: {})
    _write(tmp_path, "requirements.txt", "requests==2.0.0\n")
    rc = main([str(tmp_path), "--check-updates", "--registry", "garbage"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "ECO=VALUE" in err
