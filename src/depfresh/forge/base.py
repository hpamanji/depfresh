"""Forge abstraction: open a PR/MR and read a repo's default branch."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from depfresh.forge._http import RequestFn, Response


class ForgeError(RuntimeError):
    """A forge API call failed."""


@dataclass(frozen=True)
class RepoRef:
    """A parsed repository reference."""

    host: str
    path: str  # "owner/name" (GitHub) or "group/sub/name" (GitLab), no .git

    @property
    def owner(self) -> str:
        return self.path.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


def raise_for_status(resp: Response) -> None:
    if resp.status >= 300:
        raise ForgeError(f"forge API {resp.status}: {resp.text[:300]}")


class Forge(ABC):
    """Opens change requests against a hosted repo. One concrete impl per forge."""

    name: str = ""

    def __init__(
        self, repo: RepoRef, token: str, request: RequestFn, *, api_base: str | None = None
    ) -> None:
        self.repo = repo
        self.token = token
        self.request = request
        self.api = (api_base or self._default_api(repo.host)).rstrip("/")

    @staticmethod
    @abstractmethod
    def _default_api(host: str) -> str: ...

    @abstractmethod
    def default_branch(self) -> str: ...

    @abstractmethod
    def open_request(
        self, *, base: str, head: str, title: str, body: str, delete_source_branch: bool = True
    ) -> str:
        """Open a PR/MR from ``head`` into ``base`` and return its URL.

        If one is already open for ``head``, reuse it (refreshing title/body)
        instead of creating a duplicate. ``delete_source_branch`` asks the forge
        to remove the branch once the request merges, where supported per-request.
        """

    @abstractmethod
    def existing_request(self, head: str) -> str | None:
        """URL of an already-open request for ``head``, if any."""

    @abstractmethod
    def ensure_auto_delete_on_merge(self) -> bool:
        """Best-effort: ensure merged update branches are deleted. Returns whether
        it could be guaranteed (GitHub flips a repo setting; GitLab handles it
        per-request, so this is a no-op there)."""
