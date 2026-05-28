"""Parse a repo URL and pick the matching forge client."""

from __future__ import annotations

from depfresh_pro.forge._http import RequestFn
from depfresh_pro.forge.base import Forge, RepoRef
from depfresh_pro.forge.github import GitHubForge
from depfresh_pro.forge.gitlab import GitLabForge


def parse_repo_url(url: str) -> RepoRef:
    """Parse an https or scp-like git URL into a :class:`RepoRef`."""
    raw = url.strip()
    if "://" not in raw and "@" in raw and ":" in raw:
        # scp-like: git@host:owner/name.git
        _, _, rest = raw.partition("@")
        host, _, path = rest.partition(":")
    else:
        rest = raw.split("://", 1)[-1]
        rest = rest.split("@", 1)[-1]  # drop any user[:pass]@ userinfo
        host, _, path = rest.partition("/")
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not host or not path:
        raise ValueError(f"cannot parse repo URL: {url!r}")
    return RepoRef(host=host, path=path)


def _kind_from_host(host: str) -> str | None:
    h = host.lower()
    if "github" in h:
        return "github"
    if "gitlab" in h:
        return "gitlab"
    return None


def detect_forge(
    url: str,
    token: str,
    request: RequestFn,
    *,
    kind: str | None = None,
    api_base: str | None = None,
) -> Forge:
    """Return a forge client for ``url``. ``kind`` (github|gitlab) is required for
    self-hosted hosts whose name doesn't contain 'github'/'gitlab'."""
    repo = parse_repo_url(url)
    forge_kind = (kind or _kind_from_host(repo.host) or "").lower()
    if forge_kind == "github":
        return GitHubForge(repo, token, request, api_base=api_base)
    if forge_kind == "gitlab":
        return GitLabForge(repo, token, request, api_base=api_base)
    raise ValueError(
        f"could not determine forge for host {repo.host!r}; set the forge kind in config"
    )
