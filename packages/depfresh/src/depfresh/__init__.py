"""depfresh: a dependency scanner.

Finds dependency manifests across ecosystems and parses them into a
structured list of dependencies.
"""

from depfresh.bump import BumpPlan, build_bump_plan
from depfresh.config import DepfreshConfig, ForgeConfig, RegistryConfig, Settings, load_config
from depfresh.models import Dependency, ManifestResult, ScanResult
from depfresh.resolver import UpdateInfo, check_updates
from depfresh.scanner import scan

__version__ = "0.1.1"

__all__ = [
    "BumpPlan",
    "Dependency",
    "DepfreshConfig",
    "ForgeConfig",
    "ManifestResult",
    "RegistryConfig",
    "ScanResult",
    "Settings",
    "UpdateInfo",
    "build_bump_plan",
    "check_updates",
    "load_config",
    "scan",
    "__version__",
]
