"""Data models for scan results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Dependency:
    """A single dependency declared in a manifest file.

    ``version`` holds the constraint exactly as written in the manifest
    (e.g. ``^1.2.3``, ``>=2,<3``, ``~> 4.0``). It is ``None`` when the
    manifest pins no version.
    """

    name: str
    version: str | None
    ecosystem: str
    scope: str = "runtime"  # runtime | dev | optional | peer | build | test
    manifest: str | None = None  # source file (set by the scanner, posix-style)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ManifestResult:
    """The outcome of parsing one manifest file."""

    path: str  # path relative to scan root (posix-style)
    ecosystem: str
    manager: str  # e.g. pip, npm, cargo, go, maven, gradle, bundler, composer
    dependencies: list[Dependency] = field(default_factory=list)
    error: str | None = None  # set when parsing failed

    def to_dict(self) -> dict:
        # The per-dependency "manifest" is redundant in the grouped view (it
        # equals this manifest's path), so omit it here. The flat view keeps it.
        return {
            "path": self.path,
            "ecosystem": self.ecosystem,
            "manager": self.manager,
            "dependencies": [
                {k: v for k, v in d.to_dict().items() if k != "manifest"} for d in self.dependencies
            ],
            "error": self.error,
        }


@dataclass
class ScanResult:
    """Aggregate result of scanning a project tree."""

    root: str
    manifests: list[ManifestResult] = field(default_factory=list)

    @property
    def dependency_count(self) -> int:
        return sum(len(m.dependencies) for m in self.manifests)

    @property
    def ecosystems(self) -> list[str]:
        return sorted({m.ecosystem for m in self.manifests})

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "summary": {
                "manifest_count": len(self.manifests),
                "dependency_count": self.dependency_count,
                "ecosystems": self.ecosystems,
            },
            "manifests": [m.to_dict() for m in self.manifests],
        }
