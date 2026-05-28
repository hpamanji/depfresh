"""depfresh-pro: automated dependency-update PRs/MRs for depfresh.

This package is dual-licensed under AGPL-3.0-or-later OR a commercial license
(see LICENSE and COMMERCIAL.md). It builds on the MIT-licensed ``depfresh`` core
and depends downward on it — the core never depends on this package.
"""

from depfresh_pro.updater import UpdateGroup, UpdateRun, run_update

__version__ = "0.1.1"

__all__ = [
    "UpdateGroup",
    "UpdateRun",
    "run_update",
    "__version__",
]
