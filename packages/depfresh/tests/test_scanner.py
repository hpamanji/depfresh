"""Integration tests for the directory scanner."""

from __future__ import annotations

from depfresh.scanner import scan


def _write(base, rel, content):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_scan_multi_ecosystem_tree(tmp_path):
    _write(tmp_path, "requirements.txt", "requests==2.28.1\nflask\n")
    _write(tmp_path, "frontend/package.json", '{"dependencies": {"react": "^18.0.0"}}')
    _write(tmp_path, "svc/go.mod", "module x\nrequire github.com/foo/bar v1.0.0\n")
    # Inside an ignored dir -> must NOT be picked up.
    _write(tmp_path, "node_modules/dep/package.json", '{"dependencies": {"x": "1.0.0"}}')

    result = scan(tmp_path)
    paths = {m.path for m in result.manifests}

    assert paths == {"requirements.txt", "frontend/package.json", "svc/go.mod"}
    assert result.ecosystems == ["go", "node", "python"]
    assert result.dependency_count == 4  # 2 python + 1 node + 1 go


def test_scan_stamps_manifest_path_on_each_dependency(tmp_path):
    _write(tmp_path, "frontend/package.json", '{"dependencies": {"react": "^18.0.0"}}')
    result = scan(tmp_path)
    dep = result.manifests[0].dependencies[0]
    assert dep.name == "react"
    assert dep.manifest == "frontend/package.json"


def test_scan_records_parse_error(tmp_path):
    _write(tmp_path, "package.json", "{ this is not valid json ")
    result = scan(tmp_path)
    assert len(result.manifests) == 1
    assert result.manifests[0].error is not None
    assert result.manifests[0].dependencies == []


def test_scan_single_file(tmp_path):
    f = _write(tmp_path, "Cargo.toml", '[dependencies]\nserde = "1.0"\n')
    result = scan(f)
    assert len(result.manifests) == 1
    assert result.manifests[0].ecosystem == "rust"
    assert result.manifests[0].dependencies[0].name == "serde"


def test_scan_missing_path(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        scan(tmp_path / "does-not-exist")


def test_scan_result_to_dict(tmp_path):
    _write(tmp_path, "composer.json", '{"require": {"monolog/monolog": "^3.0"}}')
    payload = scan(tmp_path).to_dict()
    assert payload["summary"]["manifest_count"] == 1
    assert payload["summary"]["dependency_count"] == 1
    dep = payload["manifests"][0]["dependencies"][0]
    assert dep["name"] == "monolog/monolog"
    assert "manifest" not in dep  # redundant in grouped view (parent has the path)
