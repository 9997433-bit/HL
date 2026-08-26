"""Pretest planning and sensor placement (M9, spec MS-10) — Round-3 stubs.

Decides *where to put the sensors* before a test campaign is mounted, from the
target mode set of an M1 solve:

- :mod:`~openfemlab.pretest.placement` — Effective Independence (Kammer
  backward elimination on the Fisher information matrix of the sensor
  partition), the modal-kinetic-energy cross-ranking, the placement quality
  report, and the bridge to the ``SensorMap`` the M2/M4 chain consumes.

The module is **specified ahead of its implementation** (GAP-07, spec-first):
``docs/MODULE_SPEC.md`` MS-10 is the binding contract, the AC-PRETEST rows of
``docs/ACCEPTANCE_CRITERIA.md`` section 10 are all ``specified``, and every
function below raises :class:`NotImplementedError` naming its spec anchor.
Importing this package is cheap and safe; calling into it is not yet possible.
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
