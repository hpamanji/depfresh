"""Tests for the bump plan aggregation."""

from __future__ import annotations

from depfresh.bump import build_bump_plan
from depfresh.models import Dependency, ManifestResult, ScanResult
from depfresh.resolver import CURRENT, OUTDATED, UpdateInfo


def _info(ecosystem, name, latest, status=OUTDATED):
    return UpdateInfo(ecosystem, name, None, None, latest, status)


def _result():
    return ScanResult(
        root="proj",
        manifests=[
            ManifestResult(
                path="a/pyproject.toml",
                ecosystem="python",
                manager="pip",
                dependencies=[
                    Dependency("pytest", ">=8.0", "python", scope="runtime"),
                    Dependency("redis", ">=4.5", "python", scope="optional"),
                    Dependency("redis", ">=4.5", "python", scope="optional"),  # dup
                    Dependency("lonely", "==1.0", "python", scope="runtime"),
                ],
            ),
            ManifestResult(
                path="b/pyproject.toml",
                ecosystem="python",
                manager="pip",
                dependencies=[
                    Dependency("pytest", ">=7.0", "python", scope="dev"),
                    Dependency("redis", ">=5.0", "python", scope="runtime"),
                ],
            ),
            ManifestResult(
                path="c/package.json",
                ecosystem="node",
                manager="npm",
                dependencies=[Dependency("react", "^18.0.0", "node")],
            ),
        ],
    )


def _updates():
    return {
        ("python", "pytest"): _info("python", "pytest", "9.0.3"),
        ("python", "redis"): _info("python", "redis", "7.4.0"),
        ("python", "lonely"): _info("python", "lonely", "1.0", status=CURRENT),
        ("node", "react"): _info("node", "react", "19.0.0"),
    }


def test_bump_plan_groups_and_excludes_current():
    plan = build_bump_plan(_result(), _updates())
    names = [item.name for item in plan.items]
    assert "lonely" not in names  # up-to-date excluded
    assert set(names) == {"pytest", "redis", "react"}


def test_bump_plan_dedups_within_manifest():
    plan = build_bump_plan(_result(), _updates())
    redis = next(i for i in plan.items if i.name == "redis")
    # a/ listed redis twice with same constraint -> collapsed; b/ is distinct.
    assert len(redis.occurrences) == 2
    assert redis.manifest_count == 2
    assert {o.manifest for o in redis.occurrences} == {"a/pyproject.toml", "b/pyproject.toml"}


def test_bump_plan_ordered_by_blast_radius():
    plan = build_bump_plan(_result(), _updates())
    # pytest and redis touch 2 files each; react touches 1 -> react is last.
    assert plan.items[-1].name == "react"
    assert {plan.items[0].name, plan.items[1].name} == {"pytest", "redis"}


def test_bump_plan_records_per_file_constraints():
    plan = build_bump_plan(_result(), _updates())
    pytest_item = next(i for i in plan.items if i.name == "pytest")
    constraints = {(o.manifest, o.current) for o in pytest_item.occurrences}
    assert constraints == {("a/pyproject.toml", ">=8.0"), ("b/pyproject.toml", ">=7.0")}
    assert pytest_item.latest == "9.0.3"


def test_bump_plan_manifest_count_and_to_dict():
    plan = build_bump_plan(_result(), _updates())
    assert plan.manifest_count == 3  # a, b, c all touched
    payload = plan.to_dict()
    assert payload["package_count"] == 3
    assert payload["manifest_count"] == 3
    assert payload["items"][0]["occurrences"]  # has occurrence detail


def test_bump_plan_empty_when_nothing_outdated():
    updates = {("node", "react"): _info("node", "react", "18.0.0", status=CURRENT)}
    plan = build_bump_plan(_result(), updates)
    assert plan.items == []
    assert plan.manifest_count == 0
