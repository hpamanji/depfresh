"""Editor for Ruby Gemfile."""

from __future__ import annotations

from depfresh.editors.base import EditResult, Editor, replace_gemfile_dependency


class GemfileEditor(Editor):
    ecosystem = "ruby"
    filenames = ("Gemfile",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_gemfile_dependency(text, name, latest)
