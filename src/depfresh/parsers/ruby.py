"""Parsers for Ruby (Bundler) manifests."""

from __future__ import annotations

import re

from depfresh.models import Dependency
from depfresh.parsers.base import Parser

# gem 'name', '~> 1.2', '>= 1.2.1'   (version requirements are optional)
_GEM_RE = re.compile(
    r"""^\s*gem\s+['"](?P<name>[^'"]+)['"]"""
    r"""(?P<reqs>(?:\s*,\s*['"][^'"]+['"])*)"""
)
_VERSION_REQ_RE = re.compile(r"""['"]([^'"]+)['"]""")
_GROUP_RE = re.compile(r"^\s*group\s+(?P<names>[^\s]?.*?)\s+do\s*$")
# Any other block opener (platforms/source/install_if ... do), so its matching
# 'end' balances against the block instead of closing an enclosing group.
_BLOCK_OPEN_RE = re.compile(r"\bdo\b\s*(?:\|[^|]*\|)?\s*$")


class GemfileParser(Parser):
    ecosystem = "ruby"
    manager = "bundler"
    filenames = ("Gemfile",)

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        # Each frame is a group scope, or None for a non-group do...end block,
        # so an 'end' always closes the block it actually opened.
        block_stack: list[str | None] = []
        for raw in text.splitlines():
            line = raw.split("#", 1)[0]
            stripped = line.strip()
            if not stripped:
                continue

            if stripped == "end":
                if block_stack:
                    block_stack.pop()
                continue

            gm = _GROUP_RE.match(line)
            if gm:
                block_stack.append(self._group_scope(gm.group("names")))
                continue

            m = _GEM_RE.match(line)
            if m:
                # Only the requirement strings are version constraints; options
                # like ":require => false" use symbols/hashrockets, not quotes.
                reqs = _VERSION_REQ_RE.findall(m.group("reqs"))
                version = ", ".join(reqs) if reqs else None
                deps.append(
                    self._dep(m.group("name"), version, scope=self._scope(block_stack))
                )
                continue

            if _BLOCK_OPEN_RE.search(stripped):
                block_stack.append(None)
        return deps

    @staticmethod
    def _scope(block_stack: list[str | None]) -> str:
        for frame in reversed(block_stack):
            if frame is not None:
                return frame
        return "runtime"

    @staticmethod
    def _group_scope(names: str) -> str:
        lowered = names.lower()
        if "test" in lowered:
            return "test"
        if "development" in lowered or "dev" in lowered:
            return "dev"
        return "runtime"


class GemfileLockParser(Parser):
    ecosystem = "ruby"
    manager = "bundler"
    filenames = ("Gemfile.lock",)

    # Under "specs:", direct gems are indented 4 spaces: "    name (1.2.3)".
    _SPEC_RE = re.compile(r"^    (?P<name>[A-Za-z0-9._-]+) \((?P<version>[^)]+)\)\s*$")

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        in_specs = False
        for raw in text.rstrip("\n").splitlines():
            if raw.strip() == "specs:":
                in_specs = True
                continue
            if in_specs:
                m = self._SPEC_RE.match(raw)
                if m:
                    deps.append(self._dep(m.group("name"), m.group("version")))
                elif raw and not raw.startswith(" "):
                    in_specs = False  # left the GEM block
        return deps
