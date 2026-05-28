"""Thin wrapper around the ``git`` CLI (no third-party dependency).

Auth for clone/push is injected per-invocation via ``http.extraheader`` so the
token is never written to ``.git/config``. Deleting the temporary clone is the
caller's responsibility. Errors never echo the auth header.
"""

from __future__ import annotations

import base64
import subprocess
from collections.abc import Sequence
from pathlib import Path

Config = Sequence[tuple[str, str]]

# Commit identity for automated bumps. No co-author trailer is ever added.
DEFAULT_AUTHOR = ("depfresh-bot", "depfresh-bot@users.noreply.github.com")


class GitError(RuntimeError):
    """A git invocation exited non-zero."""


def auth_config(username: str, token: str) -> list[tuple[str, str]]:
    """Build a ``http.extraheader`` Basic-auth ``-c`` pair (token not persisted)."""
    raw = base64.b64encode(f"{username}:{token}".encode()).decode()
    return [("http.extraheader", f"Authorization: Basic {raw}")]


def _run(args: Sequence[str], *, cwd: str | Path | None = None, config: Config = ()) -> str:
    cmd = ["git"]
    for key, value in config:
        cmd += ["-c", f"{key}={value}"]
    if cwd is not None:
        cmd += ["-C", str(cwd)]
    cmd += list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Redacted: report the subcommand and git's stderr, never the -c config.
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def clone(url: str, dest: str | Path, *, config: Config = (), depth: int | None = 1) -> Path:
    args = ["clone"]
    if depth:
        args += ["--depth", str(depth)]
    args += [url, str(dest)]
    _run(args, config=config)
    return Path(dest)


def current_branch(repo: str | Path) -> str:
    return _run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).strip()


def remote_default_branch(repo: str | Path) -> str | None:
    """Best-effort default branch of ``origin`` from the clone's refs."""
    try:
        ref = _run(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo).strip()
    except GitError:
        return None
    return ref.rsplit("/", 1)[-1] if ref else None


def create_branch(repo: str | Path, branch: str, *, base: str | None = None) -> None:
    if base:
        _run(["checkout", base], cwd=repo)
    _run(["checkout", "-B", branch], cwd=repo)


def checkout(repo: str | Path, ref: str) -> None:
    _run(["checkout", ref], cwd=repo)


def discard_changes(repo: str | Path) -> None:
    """Revert unstaged working-tree changes (used to reset between dry-run groups)."""
    _run(["checkout", "--", "."], cwd=repo)


def stage(repo: str | Path, paths: Sequence[str | Path]) -> None:
    _run(["add", "--", *[str(p) for p in paths]], cwd=repo)


def has_staged_changes(repo: str | Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet"],
        capture_output=True,
        text=True,
    )
    return proc.returncode != 0


def commit(repo: str | Path, message: str, *, author: tuple[str, str] = DEFAULT_AUTHOR) -> None:
    name, email = author
    config = [("user.name", name), ("user.email", email)]
    _run(["commit", "-m", message], cwd=repo, config=config)


def push(
    repo: str | Path,
    branch: str,
    *,
    config: Config = (),
    remote: str = "origin",
    force: bool = False,
) -> None:
    args = ["push"]
    if force:
        args.append("--force-with-lease")
    args += ["--set-upstream", remote, branch]
    _run(args, cwd=repo, config=config)


def diff(repo: str | Path, *, staged: bool = False) -> str:
    args = ["diff"]
    if staged:
        args.append("--cached")
    return _run(args, cwd=repo)
