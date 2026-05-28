"""Editor for Rust Cargo.toml."""

from __future__ import annotations

from depfresh_pro.editors.base import EditResult, Editor, replace_toml_dependency


class CargoTomlEditor(Editor):
    ecosystem = "rust"
    filenames = ("Cargo.toml",)

    def apply(self, text: str, name: str, current: str | None, latest: str) -> EditResult:
        return replace_toml_dependency(text, name, latest)
