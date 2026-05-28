"""Tests for forge URL parsing and PR/MR clients (no network)."""

from __future__ import annotations

import json

import pytest

from depfresh.forge._http import Response
from depfresh.forge.detect import detect_forge, parse_repo_url
from depfresh.forge.github import GitHubForge
from depfresh.forge.gitlab import GitLabForge


def recording_request(routes):
    """Return (request, calls). ``routes`` is an ordered list of
    (METHOD, url-substring, Response); the first match wins, so list the more
    specific paths first."""
    calls: list[tuple] = []

    def request(method, url, *, headers=None, body=None):
        calls.append((method, url, headers or {}, body))
        for m, sub, resp in routes:
            if m == method and sub in url:
                return resp
        return Response(404, "{}")

    return request, calls


def _resp(status, payload):
    return Response(status, json.dumps(payload))


@pytest.mark.parametrize(
    "url,host,path,owner,name",
    [
        (
            "https://github.com/octocat/Hello-World.git",
            "github.com",
            "octocat/Hello-World",
            "octocat",
            "Hello-World",
        ),
        ("https://gitlab.com/group/sub/proj", "gitlab.com", "group/sub/proj", "group", "proj"),
        ("https://user:tok@github.com/o/n.git", "github.com", "o/n", "o", "n"),
        ("git@github.com:o/n.git", "github.com", "o/n", "o", "n"),
    ],
)
def test_parse_repo_url(url, host, path, owner, name):
    ref = parse_repo_url(url)
    assert (ref.host, ref.path, ref.owner, ref.name) == (host, path, owner, name)


def test_detect_forge_by_host():
    req, _ = recording_request([])
    assert isinstance(detect_forge("https://github.com/o/n", "t", req), GitHubForge)
    assert isinstance(detect_forge("https://gitlab.com/o/n", "t", req), GitLabForge)


def test_detect_forge_unknown_host_requires_kind():
    req, _ = recording_request([])
    with pytest.raises(ValueError):
        detect_forge("https://git.acme.com/o/n", "t", req)
    forge = detect_forge(
        "https://git.acme.com/o/n", "t", req, kind="gitlab", api_base="https://git.acme.com/api/v4"
    )
    assert isinstance(forge, GitLabForge)


def test_github_default_branch_and_open_pr():
    routes = [
        ("GET", "/repos/o/n", _resp(200, {"default_branch": "trunk"})),
        ("POST", "/repos/o/n/pulls", _resp(201, {"html_url": "https://github.com/o/n/pull/7"})),
    ]
    req, calls = recording_request(routes)
    forge = detect_forge("https://github.com/o/n", "tok", req)
    assert forge.default_branch() == "trunk"
    url = forge.open_request(base="trunk", head="depfresh/updates", title="Bump", body="body")
    assert url == "https://github.com/o/n/pull/7"
    post = next(c for c in calls if c[0] == "POST")
    assert post[3] == {"title": "Bump", "head": "depfresh/updates", "base": "trunk", "body": "body"}
    assert post[2]["Authorization"] == "Bearer tok"


def test_github_open_pr_returns_existing_on_422():
    routes = [
        ("GET", "/pulls?", _resp(200, [{"html_url": "https://github.com/o/n/pull/3"}])),
        ("POST", "/pulls", _resp(422, {"message": "already exists"})),
    ]
    req, _ = recording_request(routes)
    forge = detect_forge("https://github.com/o/n", "tok", req)
    assert forge.open_request(base="main", head="h", title="t", body="b").endswith("/pull/3")


def test_gitlab_default_branch_and_open_mr():
    routes = [
        # Specific paths first so the project GET doesn't shadow merge_requests.
        ("GET", "/merge_requests?", _resp(200, [])),  # none existing
        (
            "POST",
            "/merge_requests",
            _resp(201, {"web_url": "https://gitlab.com/group/proj/-/merge_requests/2"}),
        ),
        ("GET", "/projects/group%2Fproj", _resp(200, {"default_branch": "main"})),
    ]
    req, calls = recording_request(routes)
    forge = detect_forge("https://gitlab.com/group/proj", "tok", req)
    assert forge.default_branch() == "main"
    url = forge.open_request(base="main", head="depfresh/updates", title="Bump", body="desc")
    assert url.endswith("/merge_requests/2")
    post = next(c for c in calls if c[0] == "POST")
    assert post[3]["source_branch"] == "depfresh/updates"
    assert post[3]["target_branch"] == "main"


def test_gitlab_open_mr_short_circuits_when_existing():
    routes = [
        (
            "GET",
            "/merge_requests?",
            _resp(200, [{"web_url": "https://gitlab.com/g/p/-/merge_requests/9"}]),
        ),
    ]
    req, calls = recording_request(routes)
    forge = detect_forge("https://gitlab.com/g/p", "tok", req)
    url = forge.open_request(base="main", head="h", title="t", body="b")
    assert url.endswith("/merge_requests/9")
    assert not any(c[0] == "POST" for c in calls)  # no MR created
