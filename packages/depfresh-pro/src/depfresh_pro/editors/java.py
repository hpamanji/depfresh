"""Editors for JVM build manifests (Maven, Gradle)."""

from __future__ import annotations

from depfresh_pro.editors.base import (
    EditResult,
    Editor,
    replace_coordinate_dependency,
    replace_pom_dependency,
)


class PomXmlEditor(Editor):
    ecosystem = "java"
    filenames = ("pom.xml",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_pom_dependency(text, name, latest)


class GradleEditor(Editor):
    ecosystem = "java"
    patterns = ("build.gradle", "build.gradle.kts")

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_coordinate_dependency(text, name, latest)
