"""Public API contract for the reserved SSI-COV estimator."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.mpe import ssi_cov


def test_ssi_cov_reports_that_the_backend_is_not_implemented():
    responses = np.zeros((128, 2))

    with pytest.raises(NotImplementedError, match="SSI-COV operational modal analysis"):
        ssi_cov(responses, 200.0, range(2, 9, 2), block_rows=16)
