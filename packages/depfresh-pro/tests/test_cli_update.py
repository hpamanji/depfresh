"""Tests for the `depfresh update` subcommand (depfresh_pro.cli)."""

from __future__ import annotations

import json

from depfresh_pro import cli
from depfresh_pro.cli import main_update
from depfresh_pro.updater import UpdateError, UpdateGroup, UpdateRun


def test_update_passes_args_to_run_update(capsys, monkeypatch):
    captured = {}

    def fake_run_update(repo, **kw):
        captured["repo"] = repo
        captured.update(kw)
        return UpdateRun(
            repo=repo,
            base_branch="main",
            dry_run=kw.get("dry_run", False),
            groups=[
                UpdateGroup(
                    key="all",
                    branch="depfresh/updates",
                    title="Update 1 dependency",
                    items=[],
                    files_changed=["requirements.txt"],
                    request_url="https://forge/mr/1",
                    pushed=True,
                )
            ],
        )

    monkeypatch.setattr(cli, "run_update", fake_run_update)
    rc = main_update(["https://github.com/o/n", "--token", "tok", "--grouping", "dependency"])
    out = capsys.readouterr().out
    assert rc == 0
    assert captured["repo"] == "https://github.com/o/n"
    assert captured["token"] == "tok"
    assert captured["grouping"] == "dependency"
    assert "https://forge/mr/1" in out


def test_update_json_and_dry_run(capsys, monkeypatch):
    def fake_run_update(repo, **kw):
        assert kw["dry_run"] is True
        return UpdateRun(repo=repo, base_branch="main", dry_run=True, groups=[])

    monkeypatch.setattr(cli, "run_update", fake_run_update)
    rc = main_update(["https://github.com/o/n", "--dry-run", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["dry_run"] is True
    assert payload["groups"] == []


def test_update_reports_errors(capsys, monkeypatch):
    def boom(repo, **kw):
        raise UpdateError("no forge token provided")

    monkeypatch.setattr(cli, "run_update", boom)
    rc = main_update(["https://github.com/o/n"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no forge token" in err
