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
    def open_request(self, *, base: str, head: str, title: str, body: str) -> str:
        """Open (or find an existing) PR/MR from ``head`` into ``base``; return its URL."""

    @abstractmethod
    def existing_request(self, head: str) -> str | None:
        """URL of an already-open request for ``head``, if any."""
