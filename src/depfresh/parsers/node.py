"""Parsers for Node.js dependency manifests."""

from __future__ import annotations

import json

from depfresh.models import Dependency
from depfresh.parsers.base import Parser

_PACKAGE_JSON_SECTIONS = {
    "dependencies": "runtime",
    "devDependencies": "dev",
    "peerDependencies": "peer",
    "optionalDependencies": "optional",
}


class PackageJsonParser(Parser):
    ecosystem = "node"
    manager = "npm"
    filenames = ("package.json",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []
        for section, scope in _PACKAGE_JSON_SECTIONS.items():
            for name, version in (data.get(section, {}) or {}).items():
                deps.append(self._dep(name, version, scope=scope))
        return deps


class PackageLockParser(Parser):
    ecosystem = "node"
    manager = "npm"
    filenames = ("package-lock.json",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []

        # lockfileVersion >= 2/3 uses a flat "packages" map keyed by path.
        packages = data.get("packages")
        if isinstance(packages, dict):
            for path, info in packages.items():
                if not path:  # "" is the root project, not a dependency
                    continue
                name = path.split("node_modules/")[-1]
                scope = "dev" if info.get("dev") else "runtime"
                deps.append(self._dep(name, info.get("version"), scope=scope))
            return deps

        # lockfileVersion 1 uses a nested "dependencies" map.
        for name, info in (data.get("dependencies", {}) or {}).items():
            scope = "dev" if isinstance(info, dict) and info.get("dev") else "runtime"
            version = info.get("version") if isinstance(info, dict) else None
            deps.append(self._dep(name, version, scope=scope))
        return deps
