"""Editor for PHP composer.json."""

from __future__ import annotations

from depfresh_pro.editors.base import EditResult, Editor, replace_json_dependency


class ComposerJsonEditor(Editor):
    ecosystem = "php"
    filenames = ("composer.json",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_json_dependency(text, name, latest)
