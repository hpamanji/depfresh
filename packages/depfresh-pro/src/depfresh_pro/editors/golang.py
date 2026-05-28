"""Editor for Go go.mod."""

from __future__ import annotations

from depfresh_pro.editors.base import EditResult, Editor, replace_gomod_dependency


class GoModEditor(Editor):
    ecosystem = "go"
    filenames = ("go.mod",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_gomod_dependency(text, name, latest)
