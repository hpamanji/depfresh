"""Editors for Python dependency manifests."""

from __future__ import annotations

from depfresh_pro.editors.base import (
    EditResult,
    Editor,
    replace_requirements_dependency,
    replace_toml_dependency,
)


class RequirementsTxtEditor(Editor):
    ecosystem = "python"
    patterns = ("requirements*.txt", "constraints*.txt")

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_requirements_dependency(text, name, latest)


class PyprojectEditor(Editor):
    ecosystem = "python"
    filenames = ("pyproject.toml",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_toml_dependency(text, name, latest)


class PipfileEditor(Editor):
    ecosystem = "python"
    filenames = ("Pipfile",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_toml_dependency(text, name, latest)
