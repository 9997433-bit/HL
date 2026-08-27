"""Allow ``python -m openfemlab.cli`` where the console script is not on PATH."""

from __future__ import annotations

import sys

from openfemlab.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
