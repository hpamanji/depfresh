"""Base editor interface and shared text-surgery helpers.

Editors rewrite the *version* of one dependency inside a manifest's raw text.
This is deliberately text-level replacement rather than parse-and-reserialize,
which would discard comments and layout. Each helper returns ``(new_text,
changed)`` where ``changed`` is ``True`` only if something was actually rewritten.
"""

from __future__ import annotations

import fnmatch
import re
from abc import ABC, abstractmethod

from depfresh.versioning import bump_constraint

EditResult = tuple[str, bool]


class Editor(ABC):
    """Rewrites one dependency's version in a family of manifest files.

    File matching mirrors :class:`depfresh.parsers.base.Parser` (exact
    ``filenames`` and/or fnmatch ``patterns`` against the basename).
    """

    ecosystem: str = ""
    filenames: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()

    def matches(self, filename: str) -> bool:
        if filename in self.filenames:
            return True
        return any(fnmatch.fnmatch(filename, pat) for pat in self.patterns)

    @abstractmethod
    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        """Return ``(new_text, changed)`` after bumping ``name`` to ``latest``."""
        raise NotImplementedError


def _normalize(name: str) -> str:
    """PEP 503-style normalization for case/dash-insensitive name matching."""
    return re.sub(r"[-_.]+", "-", name).lower()


# --------------------------------------------------------------------------- #
# Shared replacers                                                            #
# --------------------------------------------------------------------------- #


def replace_json_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump ``"name": "version"`` entries (package.json, composer.json)."""
    pattern = re.compile(r'("' + re.escape(name) + r'"\s*:\s*")([^"]*)(")')
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        new = bump_constraint(m.group(2), latest)
        if new != m.group(2):
            changed = True
        return m.group(1) + new + m.group(3)

    return pattern.sub(repl, text), changed


def replace_toml_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump a dependency in TOML, covering the common declaration shapes:

    * table value:        ``name = "^1.0"``
    * inline-table value: ``name = { version = "^1.0", features = [...] }``
    * PEP 508 array item: ``"name>=1.0"`` (pyproject ``[project] dependencies``)
    """
    esc = re.escape(name)
    changed = False

    def bump(m: re.Match[str], ver_group: int) -> str:
        nonlocal changed
        ver = m.group(ver_group)
        new = bump_constraint(ver, latest)
        if new == ver:
            return m.group(0)
        changed = True
        start = m.start(ver_group) - m.start()
        end = m.end(ver_group) - m.start()
        whole = m.group(0)
        return whole[:start] + new + whole[end:]

    inline = re.compile(
        r'(?m)^\s*"?' + esc + r"\"?\s*=\s*\{[^}]*?version\s*=\s*[\"']([^\"']*)[\"']"
    )
    text = inline.sub(lambda m: bump(m, 1), text)

    table = re.compile(r"(?m)^(\s*\"?" + esc + r"\"?\s*=\s*)([\"'])([^\"']*)\2")
    text = table.sub(lambda m: bump(m, 3), text)

    pep508 = re.compile(r"([\"'])(" + esc + r"\s*(?:\[[^\]]*\])?\s*)([^\"';]*)\1")
    text = pep508.sub(lambda m: bump(m, 3), text)

    return text, changed


_REQ_LINE_RE = re.compile(r"^(?P<lead>\s*)(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<rest>.*)$")
# A version specifier with an explicit operator (avoids matching e.g. "win32").
_REQ_SPEC_RE = re.compile(r"(?P<op>===|==|>=|<=|~=|!=|<|>)\s*(?P<ver>[0-9][^\s,;#]*)")


def replace_requirements_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump a requirement line in requirements*.txt / constraints*.txt."""
    target = _normalize(name)
    out: list[str] = []
    changed = False
    for line in text.splitlines(keepends=True):
        m = _REQ_LINE_RE.match(line)
        if not m or _normalize(m.group("name")) != target:
            out.append(line)
            continue
        rest = m.group("rest")
        spec = _REQ_SPEC_RE.search(rest)
        if not spec:
            out.append(line)
            continue
        new_ver = latest.strip().lstrip("vV")
        if new_ver == spec.group("ver"):
            out.append(line)
            continue
        head = m.group("lead") + m.group("name")
        new_rest = rest[: spec.start("ver")] + new_ver + rest[spec.end("ver") :]
        out.append(head + new_rest)
        changed = True
    return "".join(out), changed


def replace_pom_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump the <version> of a Maven <dependency> matched by group:artifact."""
    group, sep, artifact = name.partition(":")
    if not sep:
        group, artifact = "", group
    changed = False

    def repl_block(block: str) -> str:
        nonlocal changed
        if not re.search(r"<artifactId>\s*" + re.escape(artifact) + r"\s*</artifactId>", block):
            return block
        if group and not re.search(r"<groupId>\s*" + re.escape(group) + r"\s*</groupId>", block):
            return block
        vm = re.search(r"(<version>\s*)([^<]*?)(\s*</version>)", block)
        if not vm:
            return block
        new = bump_constraint(vm.group(2), latest)
        if new == vm.group(2):
            return block
        changed = True
        return block[: vm.start()] + vm.group(1) + new + vm.group(3) + block[vm.end() :]

    new_text = re.sub(
        r"<dependency>.*?</dependency>", lambda m: repl_block(m.group(0)), text, flags=re.S
    )
    return new_text, changed


def replace_coordinate_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump the version in a quoted Gradle coordinate 'group:artifact:version'."""
    group, _, artifact = name.partition(":")
    pattern = re.compile(
        r"([\"']" + re.escape(group) + r":" + re.escape(artifact) + r":)([^\"':]+)([\"'])"
    )
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        new = bump_constraint(m.group(2), latest)
        if new != m.group(2):
            changed = True
        return m.group(1) + new + m.group(3)

    return pattern.sub(repl, text), changed


def replace_dotnet_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump a NuGet package version (Version attribute or child <Version>)."""
    esc = re.escape(name)
    changed = False

    def repl_attr(m: re.Match[str]) -> str:
        nonlocal changed
        new = bump_constraint(m.group(2), latest)
        if new != m.group(2):
            changed = True
        return m.group(1) + new + m.group(3)

    attr = re.compile(
        r'((?:Include|id)\s*=\s*"' + esc + r'"[^>]*?(?:Version|version)\s*=\s*")([^"]*)(")',
        re.IGNORECASE | re.DOTALL,
    )
    text = attr.sub(repl_attr, text)

    # Child <Version> element: <PackageReference Include="name"> <Version>V</Version>
    child = re.compile(
        r'((?:Include|id)\s*=\s*"' + esc + r'"[^>]*>\s*<Version>\s*)([^<]*?)(\s*</Version>)',
        re.IGNORECASE | re.DOTALL,
    )
    text = child.sub(repl_attr, text)
    return text, changed


_GOMOD_LINE_TMPL = r"(?m)^(\s*{name}\s+)(v[^\s/]+)(.*)$"


def replace_gomod_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump a module's version in a go.mod require directive."""
    pattern = re.compile(_GOMOD_LINE_TMPL.format(name=re.escape(name)))
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        new = bump_constraint(m.group(2), latest)
        if new != m.group(2):
            changed = True
        return m.group(1) + new + m.group(3)

    return pattern.sub(repl, text), changed


_GEM_LINE_RE = re.compile(r"""^(?P<head>\s*gem\s+['"](?P<name>[^'"]+)['"])(?P<rest>.*)$""")
_GEM_VER_RE = re.compile(r"""['"]\s*(?:[~><=!]+\s*)?(?P<ver>[0-9][^'"]*)['"]""")


def replace_gemfile_dependency(text: str, name: str, latest: str) -> EditResult:
    """Bump the first version requirement of a matching gem line in a Gemfile."""
    out: list[str] = []
    changed = False
    target = latest.strip().lstrip("vV")
    for line in text.splitlines(keepends=True):
        m = _GEM_LINE_RE.match(line.rstrip("\n"))
        if not m or m.group("name") != name:
            out.append(line)
            continue
        vm = _GEM_VER_RE.search(m.group("rest"))
        if not vm or vm.group("ver") == target:
            out.append(line)
            continue
        rest = m.group("rest")
        new_rest = rest[: vm.start("ver")] + target + rest[vm.end("ver") :]
        suffix = "\n" if line.endswith("\n") else ""
        out.append(m.group("head") + new_rest + suffix)
        changed = True
    return "".join(out), changed
