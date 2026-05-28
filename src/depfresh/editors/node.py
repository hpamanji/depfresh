"""Editor for Node.js package.json."""

from __future__ import annotations

from depfresh.editors.base import EditResult, Editor, replace_json_dependency


class PackageJsonEditor(Editor):
    ecosystem = "node"
    filenames = ("package.json",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_json_dependency(text, name, latest)
