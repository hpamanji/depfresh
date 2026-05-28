"""Registry of available editors.

Only *declared* manifests have editors; lockfiles are intentionally absent so
their occurrences are skipped (the update writes declared versions only).
"""

from __future__ import annotations

from depfresh.editors.base import Editor
from depfresh.editors.dotnet import (
    DirectoryPackagesPropsEditor,
    PackagesConfigEditor,
    ProjectFileEditor,
)
from depfresh.editors.golang import GoModEditor
from depfresh.editors.java import GradleEditor, PomXmlEditor
from depfresh.editors.node import PackageJsonEditor
from depfresh.editors.php import ComposerJsonEditor
from depfresh.editors.python import PipfileEditor, PyprojectEditor, RequirementsTxtEditor
from depfresh.editors.ruby import GemfileEditor
from depfresh.editors.rust import CargoTomlEditor

EDITORS: tuple[Editor, ...] = (
    RequirementsTxtEditor(),
    PyprojectEditor(),
    PipfileEditor(),
    PackageJsonEditor(),
    GoModEditor(),
    CargoTomlEditor(),
    PomXmlEditor(),
    GradleEditor(),
    ProjectFileEditor(),
    DirectoryPackagesPropsEditor(),
    PackagesConfigEditor(),
    ComposerJsonEditor(),
    GemfileEditor(),
)


def find_editor(filename: str) -> Editor | None:
    """Return the first editor that handles ``filename`` (basename), if any."""
    for editor in EDITORS:
        if editor.matches(filename):
            return editor
    return None
