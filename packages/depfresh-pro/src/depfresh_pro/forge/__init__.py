"""Forge (GitHub/GitLab) clients for opening dependency-update PRs/MRs."""

from depfresh_pro.forge._http import Response, make_request
from depfresh_pro.forge.base import Forge, ForgeError, RepoRef
from depfresh_pro.forge.detect import detect_forge, parse_repo_url

__all__ = [
    "Forge",
    "ForgeError",
    "RepoRef",
    "Response",
    "detect_forge",
    "make_request",
    "parse_repo_url",
]
