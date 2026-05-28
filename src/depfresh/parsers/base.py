"""Base parser interface and shared helpers."""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod

from depfresh.models import Dependency


class Parser(ABC):
    """Parses one family of manifest files into :class:`Dependency` objects.

    A parser declares the files it handles via ``filenames`` (exact, case
    sensitive matches against the basename) and/or ``patterns`` (fnmatch
    globs against the basename, e.g. ``requirements*.txt``).
    """

    ecosystem: str = ""
    manager: str = ""
    filenames: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()

    def matches(self, filename: str) -> bool:
        if filename in self.filenames:
            return True
        return any(fnmatch.fnmatch(filename, pat) for pat in self.patterns)

    @abstractmethod
    def parse(self, text: str) -> list[Dependency]:
        """Parse the manifest's text content into dependencies.

        Implementations should raise on malformed input; the scanner records
        the error against the manifest rather than aborting the whole scan.
        """
        raise NotImplementedError

    def _dep(self, name: str, version: str | None, scope: str = "runtime") -> Dependency:
        return Dependency(
            name=name.strip(),
            version=version.strip() if isinstance(version, str) and version.strip() else None,
            ecosystem=self.ecosystem,
            scope=scope,
        )
