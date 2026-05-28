"""Parsers for JVM build manifests (Maven, Gradle)."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from depfresh.models import Dependency
from depfresh.parsers.base import Parser


class PomXmlParser(Parser):
    ecosystem = "java"
    manager = "maven"
    filenames = ("pom.xml",)

    def parse(self, text: str) -> list[Dependency]:
        # "{*}" matches any namespace, sidestepping Maven's xmlns prefix.
        root = ET.fromstring(text)
        deps: list[Dependency] = []
        for dep in root.findall(".//{*}dependency"):
            group = dep.findtext("{*}groupId", default="").strip()
            artifact = dep.findtext("{*}artifactId", default="").strip()
            version = dep.findtext("{*}version", default="").strip()
            scope = dep.findtext("{*}scope", default="").strip() or "runtime"
            if not artifact:
                continue
            name = f"{group}:{artifact}" if group else artifact
            deps.append(self._dep(name, version or None, scope=scope))
        return deps


# Matches:  implementation 'g:a:v'   |   testImplementation("g:a:v")
_GRADLE_RE = re.compile(
    r"""(?P<config>\w+)\s*[\s(]\s*['"](?P<coord>[\w.\-]+:[\w.\-]+(?::[\w.\-+]+)?)['"]"""
)

_GRADLE_DEV_CONFIGS = {"testImplementation", "testCompileOnly", "testRuntimeOnly"}


class GradleParser(Parser):
    ecosystem = "java"
    manager = "gradle"
    patterns = ("build.gradle", "build.gradle.kts")

    def parse(self, text: str) -> list[Dependency]:
        deps: list[Dependency] = []
        for m in _GRADLE_RE.finditer(text):
            config = m.group("config")
            parts = m.group("coord").split(":")
            group, artifact = parts[0], parts[1]
            version = parts[2] if len(parts) > 2 else None
            scope = "test" if config in _GRADLE_DEV_CONFIGS else "runtime"
            deps.append(self._dep(f"{group}:{artifact}", version, scope=scope))
        return deps
