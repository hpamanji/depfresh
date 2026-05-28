"""Registry of available parsers.

To support a new manifest format, implement a :class:`Parser` subclass and
add an instance to ``PARSERS``.
"""

from __future__ import annotations

from depfresh.parsers.base import Parser
from depfresh.parsers.dotnet import (
    DirectoryPackagesPropsParser,
    PackagesConfigParser,
    PackagesLockJsonParser,
    ProjectFileParser,
)
from depfresh.parsers.golang import GoModParser
from depfresh.parsers.java import GradleParser, PomXmlParser
from depfresh.parsers.node import PackageJsonParser, PackageLockParser
from depfresh.parsers.php import ComposerJsonParser, ComposerLockParser
from depfresh.parsers.python import (
    PipfileLockParser,
    PipfileParser,
    PoetryLockParser,
    PyprojectParser,
    RequirementsTxtParser,
)
from depfresh.parsers.ruby import GemfileLockParser, GemfileParser
from depfresh.parsers.rust import CargoLockParser, CargoTomlParser

PARSERS: tuple[Parser, ...] = (
    # Python
    RequirementsTxtParser(),
    PyprojectParser(),
    PipfileParser(),
    PipfileLockParser(),
    PoetryLockParser(),
    # Node
    PackageJsonParser(),
    PackageLockParser(),
    # Go
    GoModParser(),
    # Rust
    CargoTomlParser(),
    CargoLockParser(),
    # Java / JVM
    PomXmlParser(),
    GradleParser(),
    # .NET / NuGet
    ProjectFileParser(),
    PackagesConfigParser(),
    DirectoryPackagesPropsParser(),
    PackagesLockJsonParser(),
    # Ruby
    GemfileParser(),
    GemfileLockParser(),
    # PHP
    ComposerJsonParser(),
    ComposerLockParser(),
)


def find_parser(filename: str) -> Parser | None:
    """Return the first parser that handles ``filename`` (basename), if any."""
    for parser in PARSERS:
        if parser.matches(filename):
            return parser
    return None
