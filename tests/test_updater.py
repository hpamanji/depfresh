"""End-to-end tests for run_update against a local bare repo + fake forge."""

from __future__ import annotations

import json
import subprocess
import urllib.error

from depfresh.updater import run_update

AUTHOR_CFG = ["-c", "user.email=t@e.st", "-c", "user.name=tester"]


class FakeForge:
    """Records forge calls instead of hitting a real API. Stateful across runs."""

    name = "github"

    def __init__(self):
        self.opened: list[dict] = []
        self.urls: dict[str, str] = {}  # head branch -> request url (open MRs)
        self.auto_delete_called = False

    def default_branch(self):
        return "main"

    def open_request(self, *, base, head, title, body, delete_source_branch=True):
        reused = head in self.urls
        url = self.urls.setdefault(head, f"https://forge.test/mr/{head}")
        self.opened.append(
            {
                "base": base,
                "head": head,
                "title": title,
                "reused": reused,
                "delete": delete_source_branch,
            }
        )
        return url

    def existing_request(self, head):
        return self.urls.get(head)

    def ensure_auto_delete_on_merge(self):
        self.auto_delete_called = True
        return True


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


def _remote_sha(remote, branch):
    return _git("rev-parse", branch, cwd=remote).stdout.strip()


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
        str(remote), token=None, forge=forge, clone_url=str(remote), fetch=_fetch(ROUTES)
    )
    assert run.base_branch == "main"
    group = run.groups[0]
    assert group.pushed and group.request_url == "https://forge.test/mr/depfresh/updates"
    assert set(group.files_changed) == {"requirements.txt", "web/package.json"}
    assert forge.auto_delete_called is True
    assert forge.opened[0]["delete"] is True
    assert "requests==2.31.0" in _remote_show(remote, "depfresh/updates", "requirements.txt")
    assert "^19.0.0" in _remote_show(remote, "depfresh/updates", "web/package.json")


def test_run_update_dry_run_makes_no_changes(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(ROUTES), dry_run=True
    )
    assert run.dry_run is True
    group = run.groups[0]
    assert group.request_url is None and group.pushed is False
    assert "2.31.0" in group.diff
    assert forge.opened == [] and forge.auto_delete_called is False
    assert "depfresh/updates" not in _remote_branches(remote)


def test_run_update_per_dependency_uses_fixed_branch_names(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run = run_update(
        str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(ROUTES), grouping="dependency"
    )
    assert len(run.groups) == 2
    branches = _remote_branches(remote)
    # Fixed names — no version suffix.
    assert "depfresh/requests" in branches
    assert "depfresh/react" in branches
    assert "depfresh/requests-2.31.0" not in branches
    assert len(forge.opened) == 2


def test_rerun_with_no_new_release_is_noop(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    forge = FakeForge()
    run_update(str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(ROUTES))
    sha_after_first = _remote_sha(remote, "depfresh/updates")

    run2 = run_update(str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(ROUTES))
    group = run2.groups[0]
    assert group.skipped_reason == "branch already up to date"
    assert group.request_url == "https://forge.test/mr/depfresh/updates"  # reused link
    assert _remote_sha(remote, "depfresh/updates") == sha_after_first  # branch untouched
    assert len(forge.opened) == 1  # no second MR created


def test_rerun_with_new_release_reuses_branch_and_mr(tmp_path):
    remote = _seed_remote(tmp_path, FILES)
    routes = {k: v for k, v in ROUTES.items()}
    forge = FakeForge()
    run_update(str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(routes))
    assert "requests==2.31.0" in _remote_show(remote, "depfresh/updates", "requirements.txt")

    # A newer release lands; same branch is force-updated and the MR is reused.
    routes["pypi.org/pypi/requests"] = {"info": {"version": "2.32.0"}}
    run2 = run_update(str(remote), forge=forge, clone_url=str(remote), fetch=_fetch(routes))
    group = run2.groups[0]
    assert group.pushed is True
    assert group.request_url == "https://forge.test/mr/depfresh/updates"
    assert "requests==2.32.0" in _remote_show(remote, "depfresh/updates", "requirements.txt")
    assert forge.opened[-1]["reused"] is True  # reused, not a new MR
    assert "depfresh/updates" in _remote_branches(remote)


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
    assert {g.key for g in run.groups} == {"requests"}
