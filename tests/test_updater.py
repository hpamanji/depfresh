"""End-to-end tests for run_update against a local bare repo + fake forge."""

from __future__ import annotations

import json
import subprocess
import urllib.error

from depfresh.updater import run_update

AUTHOR_CFG = ["-c", "user.email=t@e.st", "-c", "user.name=tester"]


class FakeForge:
    """Records open_request instead of hitting a real forge API."""

    name = "github"

    def __init__(self):
        self.opened: list[dict] = []

    def default_branch(self):
        return "main"

    def open_request(self, *, base, head, title, body):
        url = f"https://forge.test/mr/{head}"
        self.opened.append({"base": base, "head": head, "title": title, "body": body})
        return url

    def existing_request(self, head):
        return None


def _fetch(routes):
    def fetch(url, headers=None):
        for sub, payload in routes.items():
            if sub in url:
                return json.dumps(payload)
        raise urllib.error.HTTPError(url, 404, "not found", None, None)

    return fetch


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    )


def _seed_remote(tmp_path, files):
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True
    )
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-b", "main", str(seed)], check=True, capture_output=True)
    for rel, content in files.items():
        path = seed / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git("add", ".", cwd=seed)
    _git(*AUTHOR_CFG, "commit", "-m", "init", cwd=seed)
    _git("remote", "add", "origin", str(remote), cwd=seed)
    _git("push", "origin", "main", cwd=seed)
    return remote


def _remote_show(remote, branch, path):
    return _git("show", f"{branch}:{path}", cwd=remote).stdout


def _remote_branches(remote):
    return _git("branch", "--list", cwd=remote).stdout


FILES = {
    "requirements.txt": "requests==2.0.0\n",
    "web/package.json": '{\n  "dependencies": {"react": "^18.0.0"}\n}\n',
}
ROUTES = {
    "pypi.org/pypi/requests": {"info": {"version": "2.31.0"}},
    "registry.npmjs.org/react": {"dist-tags": {"latest": "19.0.0"}},
}


def test_run_update_single_mr(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote),
        token=None,
        forge=forge,
        clone_url=str(remote),
        fetch=_fetch(ROUTES),
        grouping="all",
    )
    assert run.base_branch == "main"
    assert len(run.groups) == 1
    group = run.groups[0]
    assert group.pushed and group.request_url == "https://forge.test/mr/depfresh/updates"
    assert set(group.files_changed) == {"requirements.txt", "web/package.json"}

    # The branch on the remote carries the bumped versions.
    assert "depfresh/updates" in _remote_branches(remote)
    assert "requests==2.31.0" in _remote_show(remote, "depfresh/updates", "requirements.txt")
    assert "^19.0.0" in _remote_show(remote, "depfresh/updates", "web/package.json")
    # One MR opened against main.
    assert forge.opened == [forge.opened[0]]
    assert forge.opened[0]["base"] == "main"


def test_run_update_dry_run_makes_no_changes(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote),
        forge=forge,
        clone_url=str(remote),
        fetch=_fetch(ROUTES),
        dry_run=True,
    )
    assert run.dry_run is True
    group = run.groups[0]
    assert group.request_url is None and group.pushed is False
    assert "requests" in group.diff and "2.31.0" in group.diff
    assert forge.opened == []  # nothing opened
    assert "depfresh/updates" not in _remote_branches(remote)  # nothing pushed


def test_run_update_per_dependency_grouping(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote),
        forge=forge,
        clone_url=str(remote),
        fetch=_fetch(ROUTES),
        grouping="dependency",
    )
    assert len(run.groups) == 2
    branches = _remote_branches(remote)
    assert "depfresh/requests-2.31.0" in branches
    assert "depfresh/react-19.0.0" in branches
    assert len(forge.opened) == 2


def test_run_update_exclude_skips_package(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote),
        forge=forge,
        clone_url=str(remote),
        fetch=_fetch(ROUTES),
        grouping="dependency",
        exclude=["react"],
    )
    keys = {g.key for g in run.groups}
    assert keys == {"requests"}  # react excluded
