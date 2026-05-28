"""Forge (GitHub/GitLab) clients for opening dependency-update PRs/MRs."""

from depfresh.forge._http import Response, make_request
from depfresh.forge.base import Forge, ForgeError, RepoRef
from depfresh.forge.detect import detect_forge, parse_repo_url

__all__ = [
    "Forge",
    "ForgeError",
    "RepoRef",
    "Response",
    "detect_forge",
    "make_request",
    "parse_repo_url",
]
