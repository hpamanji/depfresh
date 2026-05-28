"""Aggregate outdated dependencies into an actionable, package-centric plan.

The scan and update check are file-centric (one section per manifest). When
the same library is outdated across many manifests, you want the opposite view:
one entry per package showing the target version and every file that pins it.
That is the "bump plan".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from depfresh.models import ScanResult
from depfresh.resolver import OUTDATED, UpdateInfo


@dataclass
class BumpOccurrence:
    manifest: str  # manifest path (relative to scan root)
    current: str | None  # constraint as written in that manifest
    scope: str

    def to_dict(self) -> dict:
        return {"manifest": self.manifest, "current": self.current, "scope": self.scope}


@dataclass
class BumpItem:
    ecosystem: str
    name: str
    latest: str | None
    occurrences: list[BumpOccurrence] = field(default_factory=list)

    @property
    def manifest_count(self) -> int:
        return len({o.manifest for o in self.occurrences})

    def to_dict(self) -> dict:
        return {
            "ecosystem": self.ecosystem,
            "name": self.name,
            "latest": self.latest,
            "manifest_count": self.manifest_count,
            "occurrences": [o.to_dict() for o in self.occurrences],
        }


@dataclass
class BumpPlan:
    items: list[BumpItem] = field(default_factory=list)

    @property
    def manifest_count(self) -> int:
        return len({o.manifest for item in self.items for o in item.occurrences})

    def to_dict(self) -> dict:
        return {
            "package_count": len(self.items),
            "manifest_count": self.manifest_count,
            "items": [item.to_dict() for item in self.items],
        }


def build_bump_plan(result: ScanResult, updates: dict[tuple[str, str], UpdateInfo]) -> BumpPlan:
    """Group every outdated dependency by package, collecting where it appears.

    Items are ordered by blast radius (most files first) so the highest-impact
    bumps surface at the top.
    """
    items: dict[tuple[str, str], BumpItem] = {}
    seen: dict[tuple[str, str], set[tuple[str, str | None]]] = {}

    for manifest in result.manifests:
        for dep in manifest.dependencies:
            key = (dep.ecosystem, dep.name)
            info = updates.get(key)
            if info is None or info.status != OUTDATED:
                continue

            item = items.get(key)
            if item is None:
                item = BumpItem(dep.ecosystem, dep.name, info.latest)
                items[key] = item
                seen[key] = set()

            # Collapse exact duplicate references within the same manifest
            # (e.g. a package listed under several optional-dependency groups).
            occ_key = (manifest.path, dep.version)
            if occ_key in seen[key]:
                continue
            seen[key].add(occ_key)
            item.occurrences.append(BumpOccurrence(manifest.path, dep.version, dep.scope))

    ordered = sorted(
        items.values(),
        key=lambda i: (-len(i.occurrences), i.ecosystem, i.name.lower()),
    )
    return BumpPlan(items=ordered)
