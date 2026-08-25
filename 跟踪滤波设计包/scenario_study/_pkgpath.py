"""sys.path bootstrap for the realistic-scenario suite.

Adds (exactly once):
  跟踪滤波设计包/                       -> package-qualified imports
                                          (heterodyne_tracking_design.design_params)
  跟踪滤波设计包/homodyne_tracking_design -> flat imports (core, design_params,
                                          validate_tracking) exactly as the
                                          homodyne validators themselves do.

The homodyne core is the canonical shared DSP implementation (same layering
as matlab/: heterodyne reuses the homodyne pll_carrier_regen, which is
bit-identical to the heterodyne core's own PLL under gate='always' -- the
only gate policy the heterodyne scenarios use).
"""
import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
for _p in (str(_PARENT), str(_PARENT / 'homodyne_tracking_design')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
