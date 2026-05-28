"""Parsers for Rust (Cargo) manifests."""

from __future__ import annotations

import tomllib

from depfresh.models import Dependency
from depfresh.parsers.base import Parser

_CARGO_SECTIONS = {
    "dependencies": "runtime",
    "dev-dependencies": "dev",
    "build-dependencies": "build",
}


class CargoTomlParser(Parser):
    ecosystem = "rust"
    manager = "cargo"
    filenames = ("Cargo.toml",)

    def parse(self, text: str) -> list[Dependency]:
        data = tomllib.loads(text)
        deps: list[Dependency] = []
        for section, scope in _CARGO_SECTIONS.items():
            deps.extend(self._section(data.get(section, {}), scope))
        # target-specific deps: [target.'cfg(...)'.dependencies]
        for target in (data.get("target", {}) or {}).values():
            for section, scope in _CARGO_SECTIONS.items():
                deps.extend(self._section(target.get(section, {}), scope))
        return deps

    def _section(self, table: dict, scope: str) -> list[Dependency]:
        out: list[Dependency] = []
        for name, spec in (table or {}).items():
            version: str | None
            if isinstance(spec, str):
                version = spec
            elif isinstance(spec, dict):
                version = spec.get("version")
            else:
                version = None
            out.append(self._dep(name, version, scope=scope))
        return out


class CargoLockParser(Parser):
    ecosystem = "rust"
    manager = "cargo"
    filenames = ("Cargo.lock",)

    def parse(self, text: str) -> list[Dependency]:
        data = tomllib.loads(text)
        deps: list[Dependency] = []
        for pkg in data.get("package", []) or []:
            name = pkg.get("name")
            if name:
                deps.append(self._dep(name, pkg.get("version")))
        return deps
