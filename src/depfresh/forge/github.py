"""GitHub forge client (pull requests)."""

from __future__ import annotations

import urllib.parse

from depfresh.forge.base import Forge, raise_for_status


class GitHubForge(Forge):
    name = "github"

    @staticmethod
    def _default_api(host: str) -> str:
        # github.com -> api.github.com; GitHub Enterprise -> https://<host>/api/v3
        return "https://api.github.com" if host == "github.com" else f"https://{host}/api/v3"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "depfresh",
        }

    def default_branch(self) -> str:
        resp = self.request("GET", f"{self.api}/repos/{self.repo.path}", headers=self._headers())
        raise_for_status(resp)
        return resp.json().get("default_branch") or "main"

    def open_request(
        self, *, base: str, head: str, title: str, body: str, delete_source_branch: bool = True
    ) -> str:
        existing = self._find_open(head)
        if existing is not None:
            url, number = existing
            self.request(
                "PATCH",
                f"{self.api}/repos/{self.repo.path}/pulls/{number}",
                headers=self._headers(),
                body={"title": title, "body": body},
            )
            return url
        resp = self.request(
            "POST",
            f"{self.api}/repos/{self.repo.path}/pulls",
            headers=self._headers(),
            body={"title": title, "head": head, "base": base, "body": body},
        )
        raise_for_status(resp)
        return resp.json().get("html_url", "")

    def existing_request(self, head: str) -> str | None:
        found = self._find_open(head)
        return found[0] if found else None

    def ensure_auto_delete_on_merge(self) -> bool:
        # GitHub has no per-PR flag; deletion is a repo-level setting.
        resp = self.request(
            "PATCH",
            f"{self.api}/repos/{self.repo.path}",
            headers=self._headers(),
            body={"delete_branch_on_merge": True},
        )
        return resp.status < 300

    def _find_open(self, head: str) -> tuple[str, int] | None:
        query = urllib.parse.urlencode({"head": f"{self.repo.owner}:{head}", "state": "open"})
        resp = self.request(
            "GET", f"{self.api}/repos/{self.repo.path}/pulls?{query}", headers=self._headers()
        )
        if resp.status >= 300:
            return None
        items = resp.json()
        if not items:
            return None
        return items[0].get("html_url", ""), items[0].get("number")
