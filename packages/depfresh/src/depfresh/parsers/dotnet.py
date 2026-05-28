"""Parsers for .NET (NuGet) manifests."""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

from depfresh.models import Dependency
from depfresh.parsers.base import Parser


def _local(tag: str) -> str:
    """Strip an XML namespace prefix, e.g. '{ns}Version' -> 'Version'."""
    return tag.split("}")[-1]


def _iter_local(root: ET.Element, name: str):
    """Yield elements whose local tag name matches ``name`` (case-insensitive).

    Handles both SDK-style project files (no namespace) and legacy ones that
    use the MSBuild 2003 xmlns, without caring about element casing.
    """
    wanted = name.lower()
    for elem in root.iter():
        if _local(elem.tag).lower() == wanted:
            yield elem


def _attr(elem: ET.Element, name: str) -> str | None:
    """Case-insensitive, namespace-insensitive attribute lookup."""
    wanted = name.lower()
    for key, value in elem.attrib.items():
        if _local(key).lower() == wanted:
            return value
    return None


def _child_text(elem: ET.Element, name: str) -> str | None:
    wanted = name.lower()
    for child in elem:
        if _local(child.tag).lower() == wanted and child.text:
            return child.text.strip()
    return None


class ProjectFileParser(Parser):
    """SDK-style and legacy project files using <PackageReference>."""

    ecosystem = "dotnet"
    manager = "nuget"
    patterns = ("*.csproj", "*.fsproj", "*.vbproj")

    def parse(self, text: str) -> list[Dependency]:
        root = ET.fromstring(text)
        deps: list[Dependency] = []
        for ref in _iter_local(root, "PackageReference"):
            name = _attr(ref, "Include") or _attr(ref, "Update")
            if not name:
                continue
            # Version can be an attribute, a VersionOverride (under CPM), or a
            # child <Version> element; absent means the version is managed
            # centrally via Directory.Packages.props.
            version = (
                _attr(ref, "Version")
                or _attr(ref, "VersionOverride")
                or _child_text(ref, "Version")
            )
            deps.append(self._dep(name, version))
        return deps


class PackagesConfigParser(Parser):
    """Legacy NuGet packages.config."""

    ecosystem = "dotnet"
    manager = "nuget"
    filenames = ("packages.config",)

    def parse(self, text: str) -> list[Dependency]:
        root = ET.fromstring(text)
        deps: list[Dependency] = []
        for pkg in _iter_local(root, "package"):
            name = _attr(pkg, "id")
            if not name:
                continue
            is_dev = (_attr(pkg, "developmentDependency") or "").lower() == "true"
            deps.append(
                self._dep(name, _attr(pkg, "version"), scope="dev" if is_dev else "runtime")
            )
        return deps


class DirectoryPackagesPropsParser(Parser):
    """Central Package Management: <PackageVersion> entries."""

    ecosystem = "dotnet"
    manager = "nuget"
    filenames = ("Directory.Packages.props",)

    def parse(self, text: str) -> list[Dependency]:
        root = ET.fromstring(text)
        deps: list[Dependency] = []
        for pv in _iter_local(root, "PackageVersion"):
            name = _attr(pv, "Include")
            if not name:
                continue
            version = _attr(pv, "Version") or _child_text(pv, "Version")
            deps.append(self._dep(name, version))
        return deps


class PackagesLockJsonParser(Parser):
    """NuGet lock file (packages.lock.json)."""

    ecosystem = "dotnet"
    manager = "nuget"
    filenames = ("packages.lock.json",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []
        # { "dependencies": { "<framework>": { "<pkg>": {type, resolved, ...} } } }
        for packages in (data.get("dependencies", {}) or {}).values():
            for name, info in (packages or {}).items():
                if not isinstance(info, dict):
                    continue
                version = info.get("resolved") or info.get("requested")
                scope = "indirect" if info.get("type") == "Transitive" else "runtime"
                deps.append(self._dep(name, version, scope=scope))
        return deps
