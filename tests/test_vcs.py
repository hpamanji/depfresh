"""Tests for the git wrapper, using a local bare repo as the 'remote'."""

from __future__ import annotations

import subprocess

from depfresh import vcs

AUTHOR_CFG = ["-c", "user.email=t@e.st", "-c", "user.name=tester"]


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    )


def _seed_remote(tmp_path):
    """Create a bare repo seeded with one commit on main; return its path."""
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True
    )
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-b", "main", str(seed)], check=True, capture_output=True)
    (seed / "requirements.txt").write_text("requests==2.0.0\n", encoding="utf-8")
    _git("add", ".", cwd=seed)
    _git(*AUTHOR_CFG, "commit", "-m", "init", cwd=seed)
    _git("remote", "add", "origin", str(remote), cwd=seed)
    _git("push", "origin", "main", cwd=seed)
    return remote


def test_clone_and_default_branch(tmp_path):
    remote = _seed_remote(tmp_path)
    work = tmp_path / "work"
    vcs.clone(str(remote), work, depth=None)
    assert (work / "requirements.txt").exists()
    assert vcs.current_branch(work) == "main"
    assert vcs.remote_default_branch(work) == "main"


def test_branch_commit_push_roundtrip(tmp_path):
    remote = _seed_remote(tmp_path)
    work = tmp_path / "work"
    vcs.clone(str(remote), work, depth=None)

    vcs.create_branch(work, "depfresh/updates")
    (work / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    vcs.stage(work, ["requirements.txt"])
    assert vcs.has_staged_changes(work) is True
    vcs.commit(work, "Bump requests")
    vcs.push(work, "depfresh/updates")

    # The branch now exists on the remote with the new content.
    branches = _git("branch", "--list", cwd=remote).stdout
    assert "depfresh/updates" in branches
    show = _git("show", "depfresh/updates:requirements.txt", cwd=remote).stdout
    assert "2.31.0" in show


def test_has_staged_changes_false_when_clean(tmp_path):
    remote = _seed_remote(tmp_path)
    work = tmp_path / "work"
    vcs.clone(str(remote), work, depth=None)
    assert vcs.has_staged_changes(work) is False


def test_auth_config_builds_basic_header_without_persisting():
    cfg = vcs.auth_config("x-access-token", "secret-tok")
    assert cfg[0][0] == "http.extraheader"
    assert cfg[0][1].startswith("Authorization: Basic ")
    assert "secret-tok" not in cfg[0][1]  # base64-encoded, not plaintext


def test_git_error_is_redacted(tmp_path):
    import pytest

    with pytest.raises(vcs.GitError) as exc:
        vcs.clone(
            "https://example.invalid/nope.git",
            tmp_path / "x",
            config=vcs.auth_config("u", "topsecret"),
            depth=1,
        )
    assert "topsecret" not in str(exc.value)
