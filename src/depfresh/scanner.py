"""Project tree scanner: walks a directory and parses manifests it finds."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from depfresh.models import ManifestResult, ScanResult
from depfresh.registry import find_parser

# Directories never worth descending into: VCS metadata, virtualenvs, and
# vendored dependency trees (which hold transitive manifests, not the
# project's own declared dependencies).
DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        "bower_components",
        "vendor",
        "target",
        "build",
        "dist",
        ".gradle",
        ".idea",
        ".vscode",
    }
)

# Manifests above this size are almost certainly not hand-written; parsing a
# huge lockfile is allowed but we cap to avoid pathological memory use.
_MAX_FILE_BYTES = 20 * 1024 * 1024


def scan(
    root: str | os.PathLike[str],
    *,
    ignore_dirs: frozenset[str] | None = None,
    follow_symlinks: bool = False,
) -> ScanResult:
    """Scan ``root`` for dependency manifests and parse them.

    Returns a :class:`ScanResult`. Parse failures are recorded per-manifest
    (``ManifestResult.error``) rather than raising.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"path does not exist: {root_path}")

    ignore = ignore_dirs if ignore_dirs is not None else DEFAULT_IGNORE_DIRS
    result = ScanResult(root=str(root_path))

    if root_path.is_file():
        manifest = _scan_file(root_path, root_path.parent)
        if manifest:
            result.manifests.append(manifest)
        return result

    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=follow_symlinks):
        # Prune ignored directories in place so os.walk skips them.
        dirnames[:] = [d for d in dirnames if d not in ignore]
        for filename in filenames:
            parser_present = find_parser(filename) is not None
            if not parser_present:
                continue
            manifest = _scan_file(Path(dirpath) / filename, root_path)
            if manifest:
                result.manifests.append(manifest)

    result.manifests.sort(key=lambda m: m.path)
    return result


def _scan_file(file_path: Path, root_path: Path) -> ManifestResult | None:
    parser = find_parser(file_path.name)
    if parser is None:
        return None

    rel = _relpath(file_path, root_path)
    manifest = ManifestResult(path=rel, ecosystem=parser.ecosystem, manager=parser.manager)
    try:
        if file_path.stat().st_size > _MAX_FILE_BYTES:
            manifest.error = "file too large to parse"
            return manifest
        text = file_path.read_text(encoding="utf-8", errors="replace")
        # Stamp each dependency with the file it was found in.
        manifest.dependencies = [replace(dep, manifest=rel) for dep in parser.parse(text)]
    except Exception as exc:  # noqa: BLE001 - surface any parse error per-file
        manifest.error = f"{type(exc).__name__}: {exc}"
    return manifest


def _relpath(file_path: Path, root_path: Path) -> str:
    try:
        rel = file_path.relative_to(root_path)
    except ValueError:
        rel = file_path
    return rel.as_posix()
