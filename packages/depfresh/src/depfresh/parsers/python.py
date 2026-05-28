"""Parsers for Python dependency manifests."""

from __future__ import annotations

import json
import re
import tomllib

from depfresh.models import Dependency
from depfresh.parsers.base import Parser

# PEP 508: name then optional [extras] then the version specifier up to a marker.
_PEP508_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)"
    r"\s*(?:\[[^\]]*\])?"
    r"\s*(?P<spec>[^;]*)"
)


def _split_requirement(req: str) -> tuple[str, str | None] | None:
    """Split a PEP 508 requirement string into (name, version_spec)."""
    req = req.strip()
    if not req or req.startswith("#"):
        return None
    m = _PEP508_RE.match(req)
    if not m:
        return None
    name = m.group("name")
    spec = m.group("spec").strip().strip("()").strip()
    return name, (spec or None)


class RequirementsTxtParser(Parser):
    ecosystem = "python"
    manager = "pip"
    patterns = ("requirements*.txt", "constraints*.txt")

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Skip pip options (-r, -e, --hash, etc.) and direct URLs/paths.
            if line.startswith("-") or "://" in line or line.startswith((".", "/")):
                continue
            line = line.split("#", 1)[0].strip()  # strip trailing comments
            # Drop inline pip options trailing the requirement (e.g. "--hash=...").
            line = re.split(r"\s-{1,2}[A-Za-z]", line, maxsplit=1)[0].strip()
            parsed = _split_requirement(line)
            if parsed:
                name, version = parsed
                deps.append(self._dep(name, version))
        return deps


class PyprojectParser(Parser):
    ecosystem = "python"
    manager = "pip"
    filenames = ("pyproject.toml",)

    def parse(self, text: str) -> list[Dependency]:
        data = tomllib.loads(text)
        deps: list[Dependency] = []

        # PEP 621 [project]
        project = data.get("project", {})
        for req in project.get("dependencies", []) or []:
            parsed = _split_requirement(req)
            if parsed:
                deps.append(self._dep(parsed[0], parsed[1]))
        for group, reqs in (project.get("optional-dependencies", {}) or {}).items():
            for req in reqs or []:
                parsed = _split_requirement(req)
                if parsed:
                    deps.append(self._dep(parsed[0], parsed[1], scope="optional"))

        # Poetry [tool.poetry]
        poetry = data.get("tool", {}).get("poetry", {})
        if poetry:
            deps.extend(self._poetry_deps(poetry.get("dependencies", {}), "runtime"))
            deps.extend(self._poetry_deps(poetry.get("dev-dependencies", {}), "dev"))
            for grp in (poetry.get("group", {}) or {}).values():
                scope = "dev"
                deps.extend(self._poetry_deps(grp.get("dependencies", {}), scope))

        return deps

    def _poetry_deps(self, table: dict, scope: str) -> list[Dependency]:
        out: list[Dependency] = []
        for name, spec in (table or {}).items():
            if name.lower() == "python":
                continue
            version = self._poetry_version(spec)
            out.append(self._dep(name, version, scope=scope))
        return out

    @staticmethod
    def _poetry_version(spec) -> str | None:
        if isinstance(spec, str):
            return spec
        if isinstance(spec, dict):
            return spec.get("version")
        return None


class PipfileParser(Parser):
    ecosystem = "python"
    manager = "pipenv"
    filenames = ("Pipfile",)

    def parse(self, text: str) -> list[Dependency]:
        data = tomllib.loads(text)
        deps: list[Dependency] = []
        deps.extend(self._section(data.get("packages", {}), "runtime"))
        deps.extend(self._section(data.get("dev-packages", {}), "dev"))
        return deps

    def _section(self, table: dict, scope: str) -> list[Dependency]:
        out: list[Dependency] = []
        for name, spec in (table or {}).items():
            if isinstance(spec, dict):
                version = spec.get("version")
            else:
                version = spec
            if version in ("*", "", None):
                version = None
            out.append(self._dep(name, version, scope=scope))
        return out


class PoetryLockParser(Parser):
    ecosystem = "python"
    manager = "poetry"
    filenames = ("poetry.lock",)

    def parse(self, text: str) -> list[Dependency]:
        data = tomllib.loads(text)
        deps: list[Dependency] = []
        for pkg in data.get("package", []) or []:
            name = pkg.get("name")
            if not name:
                continue
            scope = "dev" if pkg.get("category") == "dev" else "runtime"
            deps.append(self._dep(name, pkg.get("version"), scope=scope))
        return deps


class PipfileLockParser(Parser):
    ecosystem = "python"
    manager = "pipenv"
    filenames = ("Pipfile.lock",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []
        for section, scope in (("default", "runtime"), ("develop", "dev")):
            for name, spec in (data.get(section, {}) or {}).items():
                version = spec.get("version") if isinstance(spec, dict) else None
                deps.append(self._dep(name, version, scope=scope))
        return deps
