"""GitLab forge client (merge requests)."""

from __future__ import annotations

import urllib.parse

from depfresh.forge._http import RequestFn
from depfresh.forge.base import Forge, RepoRef, raise_for_status


class GitLabForge(Forge):
    name = "gitlab"

    def __init__(
        self, repo: RepoRef, token: str, request: RequestFn, *, api_base: str | None = None
    ) -> None:
        super().__init__(repo, token, request, api_base=api_base)
        # GitLab addresses projects by URL-encoded full path.
        self.project_id = urllib.parse.quote(repo.path, safe="")

    @staticmethod
    def _default_api(host: str) -> str:
        return "https://gitlab.com/api/v4" if host == "gitlab.com" else f"https://{host}/api/v4"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "User-Agent": "depfresh"}

    def default_branch(self) -> str:
        resp = self.request(
            "GET", f"{self.api}/projects/{self.project_id}", headers=self._headers()
        )
        raise_for_status(resp)
        return resp.json().get("default_branch") or "main"

    def open_request(
        self, *, base: str, head: str, title: str, body: str, delete_source_branch: bool = True
    ) -> str:
        existing = self._find_open(head)
        if existing is not None:
            url, iid = existing
            self.request(
                "PUT",
                f"{self.api}/projects/{self.project_id}/merge_requests/{iid}",
                headers=self._headers(),
                body={
                    "title": title,
                    "description": body,
                    "remove_source_branch": delete_source_branch,
                },
            )
            return url
        resp = self.request(
            "POST",
            f"{self.api}/projects/{self.project_id}/merge_requests",
            headers=self._headers(),
            body={
                "source_branch": head,
                "target_branch": base,
                "title": title,
                "description": body,
                "remove_source_branch": delete_source_branch,
            },
        )
        raise_for_status(resp)
        return resp.json().get("web_url", "")

    def existing_request(self, head: str) -> str | None:
        found = self._find_open(head)
        return found[0] if found else None

    def ensure_auto_delete_on_merge(self) -> bool:
        # Handled per-request via remove_source_branch in open_request.
        return True

    def _find_open(self, head: str) -> tuple[str, int] | None:
        query = urllib.parse.urlencode({"source_branch": head, "state": "opened"})
        resp = self.request(
            "GET",
            f"{self.api}/projects/{self.project_id}/merge_requests?{query}",
            headers=self._headers(),
        )
        if resp.status >= 300:
            return None
        items = resp.json()
        if not items:
            return None
        return items[0].get("web_url", ""), items[0].get("iid")
