"""Registry of available editors.

Only *declared* manifests have editors; lockfiles are intentionally absent so
their occurrences are skipped (the update writes declared versions only).
"""

from __future__ import annotations

from depfresh_pro.editors.base import Editor
from depfresh_pro.editors.dotnet import (
    DirectoryPackagesPropsEditor,
    PackagesConfigEditor,
    ProjectFileEditor,
)
from depfresh_pro.editors.golang import GoModEditor
from depfresh_pro.editors.java import GradleEditor, PomXmlEditor
from depfresh_pro.editors.node import PackageJsonEditor
from depfresh_pro.editors.php import ComposerJsonEditor
from depfresh_pro.editors.python import PipfileEditor, PyprojectEditor, RequirementsTxtEditor
from depfresh_pro.editors.ruby import GemfileEditor
from depfresh_pro.editors.rust import CargoTomlEditor

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
