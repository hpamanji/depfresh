"""Make both src-layout packages importable in tests without installation."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
for _pkg in ("depfresh", "depfresh-pro"):
    _src = ROOT / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
