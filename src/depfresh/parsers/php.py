"""Parsers for PHP (Composer) manifests."""

from __future__ import annotations

import json

from depfresh.models import Dependency
from depfresh.parsers.base import Parser


def _is_platform_requirement(name: str) -> bool:
    """php, hhvm, ext-*, lib-* are platform packages, not Composer deps."""
    lowered = name.lower()
    return lowered in ("php", "hhvm") or lowered.startswith(("ext-", "lib-"))


class ComposerJsonParser(Parser):
    ecosystem = "php"
    manager = "composer"
    filenames = ("composer.json",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []
        for section, scope in (("require", "runtime"), ("require-dev", "dev")):
            for name, version in (data.get(section, {}) or {}).items():
                if _is_platform_requirement(name):
                    continue
                deps.append(self._dep(name, version, scope=scope))
        return deps


class ComposerLockParser(Parser):
    ecosystem = "php"
    manager = "composer"
    filenames = ("composer.lock",)

    def parse(self, text: str) -> list[Dependency]:
        data = json.loads(text)
        deps: list[Dependency] = []
        for section, scope in (("packages", "runtime"), ("packages-dev", "dev")):
            for pkg in (data.get(section, []) or []):
                name = pkg.get("name")
                if name and not _is_platform_requirement(name):
                    deps.append(self._dep(name, pkg.get("version"), scope=scope))
        return deps
