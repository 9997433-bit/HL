"""Modal analysis layer (L2): eigen-extraction and mode post-processing.

Round 1 ships a working sparse eigensolver wrapper (:func:`solve_modes`).
Round 2 adds mass normalization utilities and effective modal mass; Round 3
targets modal parameter extraction (MPE) from measured FRFs.
"""

from openfemlab.modal.eigen import solve_modes

__all__ = ["solve_modes"]
