"""Minimal HTTP helper for forge API calls (GET/POST JSON), injectable for tests.

Mirrors the ``fetch`` indirection in :mod:`depfresh.resolver`: forge clients call
through a ``RequestFn`` so tests can supply canned responses with no network.
"""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Response:
    status: int
    text: str

    def json(self) -> Any:
        return _json.loads(self.text) if self.text.strip() else {}


class RequestFn(Protocol):
    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = ...,
        body: dict[str, Any] | None = ...,
    ) -> Response: ...


def make_request(timeout: float = 15.0) -> RequestFn:
    """Build a real HTTP requester. 4xx/5xx are returned (not raised) as a
    :class:`Response` so callers can branch on status (e.g. 422 = PR exists)."""

    def request(
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Response:
        data = None
        hdrs = dict(headers or {})
        if body is not None:
            data = _json.dumps(body).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return Response(resp.status, resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return Response(exc.code, exc.read().decode("utf-8", "replace"))

    return request
