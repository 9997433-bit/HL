"""Operational modal analysis with SSI-COV (AC-MPE-006).

Simulates ambient vibration of a two-mode system, identifies poles with
SSI-COV, and compares recovered frequencies to the oracle values.

Run::

    python examples/08_ssi_oma.py
"""

from __future__ import annotations

import numpy as np

from openfemlab.mpe.ssi import simulate_operational_response, ssi_cov

TRUTH_FREQS = (4.0, 9.5)
TRUTH_DAMP = (0.015, 0.02)
SHAPES = np.array([[1.0, 0.8], [1.2, -0.6], [0.7, 1.1]])
FS = 200.0
SAMPLES = 8192
TOL_HZ = 0.6


def main() -> None:
    record = simulate_operational_response(
        TRUTH_FREQS,
        TRUTH_DAMP,
        SHAPES,
        sampling_rate_hz=FS,
        samples=SAMPLES,
        seed=17,
    )
    result = ssi_cov(
        record,
        FS,
        range(6, 20, 2),
        block_rows=30,
        min_count=2,
        freq_tol=0.05,
        damp_tol=0.15,
        mac_tol=0.85,
    )
    identified = sorted(float(f) for f in result.frequencies_hz)
    truth = list(TRUTH_FREQS)

    print("SSI-COV operational modal analysis")
    print(f"  record shape : {record.shape}")
    print(f"  truth freqs  : {truth} Hz")
    print(f"  identified   : {[round(f, 3) for f in identified]} Hz")

    for freq in truth:
        nearest = min(identified, key=lambda value: abs(value - freq))
        error = abs(nearest - freq)
        status = "ok" if error <= TOL_HZ else "FAIL"
        print(f"  {freq:.1f} Hz -> {nearest:.3f} Hz (|df|={error:.3f}) [{status}]")


if __name__ == "__main__":
    main()
