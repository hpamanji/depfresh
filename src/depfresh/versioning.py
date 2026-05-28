"""Best-effort, ecosystem-agnostic version handling.

This is deliberately approximate: it covers the dotted-numeric + pre-release
shape that the vast majority of real versions use (PEP 440, SemVer, NuGet,
Maven). It is not a full implementation of any one ecosystem's spec, so the
"outdated" flag should be read as a strong hint, not a guarantee.
"""

from __future__ import annotations

import re

# Matches a leading dotted-numeric release, e.g. "1", "1.2", "18.2.0", "4.5.1.2".
_RELEASE_RE = re.compile(r"\d+(?:\.\d+)*")

# Pre-release markers anywhere in the version string.
_PRERELEASE_RE = re.compile(r"(?i)(alpha|beta|rc|dev|pre|snapshot|[ab]\d|-pre|preview)")

# A version-looking token inside a constraint, e.g. "13.0.1" in ">=13.0.1,<14".
_VERSION_TOKEN_RE = re.compile(r"\d+(?:\.\d+)*(?:[.\-][0-9A-Za-z]+)*")

_UNCOMPARABLE_PREFIXES = ("git", "http", "file:", "github:", "npm:", "link:", "workspace:")


def extract_current_version(constraint: str | None) -> str | None:
    """Pull a comparable version out of a constraint string.

    Strips operators/ranges and returns the first concrete version token, e.g.
    ``^18.2.0`` -> ``18.2.0``, ``>=3.2,<4`` -> ``3.2``, ``[13.0.1, )`` ->
    ``13.0.1``. Returns ``None`` for wildcards, URLs, or anything with no
    recognisable version.
    """
    if not constraint:
        return None
    text = constraint.strip()
    if text in ("*", "", "latest", "x") or text.lower().startswith(_UNCOMPARABLE_PREFIXES):
        return None
    match = _VERSION_TOKEN_RE.search(text)
    return match.group(0) if match else None


def _version_key(version: str) -> tuple[list[int], bool]:
    """Return (release_segments, is_prerelease) for comparison."""
    cleaned = version.strip().lstrip("vV").split("+", 1)[0]  # drop build metadata
    match = _RELEASE_RE.match(cleaned)
    release = [int(p) for p in match.group(0).split(".")] if match else [0]
    is_prerelease = bool(_PRERELEASE_RE.search(cleaned))
    return release, is_prerelease


def compare(a: str, b: str) -> int:
    """Return -1 if a < b, 0 if equal, 1 if a > b (best effort)."""
    release_a, pre_a = _version_key(a)
    release_b, pre_b = _version_key(b)

    width = max(len(release_a), len(release_b))
    release_a += [0] * (width - len(release_a))
    release_b += [0] * (width - len(release_b))

    if release_a != release_b:
        return -1 if release_a < release_b else 1
    if pre_a != pre_b:
        # same release numbers: a pre-release sorts below the final release.
        return -1 if pre_a and not pre_b else 1
    return 0


def is_outdated(current: str | None, latest: str | None) -> bool:
    if not current or not latest:
        return False
    try:
        return compare(current, latest) < 0
    except Exception:  # noqa: BLE001 - never let version quirks crash a scan
        return False
