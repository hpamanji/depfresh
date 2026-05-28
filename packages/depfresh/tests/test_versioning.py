"""Tests for version extraction and comparison."""

from __future__ import annotations

import pytest

from depfresh.versioning import bump_constraint, compare, extract_current_version, is_outdated


@pytest.mark.parametrize(
    "constraint,expected",
    [
        ("^18.2.0", "18.2.0"),
        (">=3.2,<4", "3.2"),
        ("~> 7.0.4", "7.0.4"),
        ("==2.28.1", "2.28.1"),
        ("[13.0.1, )", "13.0.1"),
        ("13.0.1", "13.0.1"),
        ("v1.9.1", "1.9.1"),
        ("*", None),
        ("", None),
        (None, None),
        ("git+https://example.com/x.git", None),
        ("workspace:*", None),
    ],
)
def test_extract_current_version(constraint, expected):
    assert extract_current_version(constraint) == expected


@pytest.mark.parametrize(
    "a,b,sign",
    [
        ("1.0.0", "1.0.1", -1),
        ("2.0.0", "1.9.9", 1),
        ("1.2.0", "1.2", 0),  # trailing zero padding
        ("1.0.0", "1.0.0", 0),
        ("18.2.0", "19.0.0", -1),
        ("2.0.0-rc1", "2.0.0", -1),  # pre-release < final
        ("2.0.0", "2.0.0-rc1", 1),
        ("v1.2.3", "1.2.3", 0),  # leading v ignored
    ],
)
def test_compare(a, b, sign):
    result = compare(a, b)
    assert (result > 0) == (sign > 0)
    assert (result < 0) == (sign < 0)
    assert (result == 0) == (sign == 0)


def test_is_outdated():
    assert is_outdated("1.0.0", "2.0.0") is True
    assert is_outdated("2.0.0", "2.0.0") is False
    assert is_outdated("2.1.0", "2.0.0") is False
    assert is_outdated(None, "2.0.0") is False
    assert is_outdated("1.0.0", None) is False


@pytest.mark.parametrize(
    "current,latest,expected",
    [
        ("^18.2.0", "19.0.0", "^19.0.0"),
        ("==2.28.1", "2.31.0", "==2.31.0"),
        ("~> 7.0.4", "7.1.0", "~> 7.1.0"),
        ("v1.2.3", "v1.9.0", "v1.9.0"),  # go: leading v preserved, no doubling
        ("1.2.3", "1.9.0", "1.9.0"),  # bare pin
        (">=3.2,<4", "3.9.1", ">=3.9.1,<4"),  # range: in-bounds lower bump
        (">=1.0,<2.0", "2.5.0", ">=1.0,<2.0"),  # range: crossing upper -> untouched
        (">=1.2,<1.20", "1.25", ">=1.2,<1.20"),  # range: crossing upper -> untouched
        (">=1.0,<=2.0", "2.0", ">=1.0,<=2.0"),  # range: hits upper bound -> untouched
        ("1.0.0 - 2.0.0", "1.5.0", "1.5.0 - 2.0.0"),  # hyphen range: in-bounds bump
        ("1.0.0 - 2.0.0", "2.5.0", "1.0.0 - 2.0.0"),  # hyphen range: crossing -> untouched
        ("*", "5.0.0", "*"),  # wildcard left alone
        ("", "5.0.0", "5.0.0"),  # empty -> latest verbatim
        (None, "5.0.0", "5.0.0"),
    ],
)
def test_bump_constraint(current, latest, expected):
    assert bump_constraint(current, latest) == expected
