"""Enable `python -m depfresh`."""

import sys

from depfresh.cli import main

if __name__ == "__main__":
    sys.exit(main())
