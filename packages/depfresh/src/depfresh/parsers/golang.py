"""Parser for Go module manifests (go.mod)."""

from __future__ import annotations

import re

from depfresh.models import Dependency
from depfresh.parsers.base import Parser

# e.g. "github.com/foo/bar v1.2.3" optionally followed by "// indirect"
_REQUIRE_RE = re.compile(r"^(?P<path>[^\s]+)\s+(?P<version>v[^\s]+)(?P<comment>\s*//.*)?$")


class GoModParser(Parser):
    ecosystem = "go"
    manager = "go"
    filenames = ("go.mod",)

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        in_require_block = False
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue

            if in_require_block:
                if line == ")":
                    in_require_block = False
                    continue
                self._add(deps, line)
                continue

            if line.startswith("require"):
                rest = line[len("require") :].strip()
                if rest.startswith("("):
                    in_require_block = True
                    continue
                if rest:
                    self._add(deps, rest)
        return deps

    def _add(self, deps: list[Dependency], line: str) -> None:
        m = _REQUIRE_RE.match(line)
        if not m:
            return
        scope = "indirect" if m.group("comment") and "indirect" in m.group("comment") else "runtime"
        deps.append(self._dep(m.group("path"), m.group("version"), scope=scope))
