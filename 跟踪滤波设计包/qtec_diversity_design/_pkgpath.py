"""sys.path bootstrap: make the sibling homodyne_tracking_design importable.

The qtec modules reuse homodyne_tracking_design.core / design_params
directly (PEP 420 namespace package -- no __init__.py needed, nothing in
the homodyne folder is modified).  Importing this module inserts the
parent folder (跟踪滤波设计包/) into sys.path exactly once.

No circular import is possible: homodyne_tracking_design never imports
anything from qtec_diversity_design.
"""
import sys
from pathlib import Path

_PKG_PARENT = str(Path(__file__).resolve().parent.parent)
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)
