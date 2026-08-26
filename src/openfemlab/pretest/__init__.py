"""Pretest planning and sensor placement (M10, spec MS-11) — Round-3 stubs.

Decides *where to put the sensors* before a test campaign is mounted, from the
target mode set of an M1 solve:

- :mod:`~openfemlab.pretest.placement` — Effective Independence (Kammer
  backward elimination on the Fisher information matrix of the sensor
  partition), the modal-kinetic-energy cross-ranking, the placement quality
  report, and the bridge to the ``SensorMap`` the M2/M4 chain consumes.

The module is **specified ahead of its implementation** (GAP-07, spec-first):
``docs/MODULE_SPEC.md`` MS-11 is the binding contract, the AC-PRETEST rows of
``docs/ACCEPTANCE_CRITERIA.md`` section 11 gate the implementation, and
``method="adpr"`` remains reserved for the MS-11.3 P2 outline.
"""

from ..exceptions import PretestError
from .placement import (
    PlacementQuality,
    PlacementResult,
    ei_leverage,
    modal_kinetic_energy,
    placement_quality,
    select_sensors,
    to_sensor_map,
)

__all__ = [
    "PlacementQuality",
    "PlacementResult",
    "PretestError",
    "ei_leverage",
    "modal_kinetic_energy",
    "placement_quality",
    "select_sensors",
    "to_sensor_map",
]
