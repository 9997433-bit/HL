"""FE ↔ test DOF alignment (MS-2.1).

Correlation metrics need both mode sets expressed on *one* DOF set. A test
article is instrumented with a handful of accelerometers while the FE model
may carry millions of DOFs, so the shared set is the sensor set and the FE
shapes are reduced onto it by the selection operator ``T``:

``Φ_fe,reduced = T Φ_fe``   with   ``T[i, k] = sign_i`` for sensor ``i`` at FE row ``k``

This module only performs *reduction* by row selection (the default). Matrix
reduction onto the sensor set and SEREP expansion of test shapes to the full FE
space live in :mod:`openfemlab.correlation.reduction` and consume the same row
indices this module produces.

Two entry points cover the two ways rows are identified: by
:class:`~openfemlab.core.dofs.DofMap` (``(node_id, DofType)`` pairs — the
platform's native contract) and by free-form string labels such as
``"node_3:x"``, which is what most external test files carry.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
import numpy.typing as npt

from openfemlab.correlation.mac import as_columns

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps correlation core-free
    from openfemlab.core.dofs import DofMap

__all__ = [
    "AlignedShapes",
    "align_by_labels",
    "align_dof_maps",
    "align_modal_data",
    "align_shapes",
    "selection_matrix",
]


class HasShapesAndDofMap(Protocol):
    """Structural type of :class:`~openfemlab.core.results.ModalResult` and ``TestData``."""

    shapes: Any
    dof_map: Any


@dataclass(frozen=True)
class AlignedShapes:
    """Two mode-shape sets reduced onto their shared DOFs.

    Attributes
    ----------
    test, fe:
        ``(s, m_test)`` and ``(s, m_fe)`` shape matrices on the ``s`` shared
        DOFs, in test-channel order.
    test_rows, fe_rows:
        Row indices of the shared DOFs in the original test and FE sets.
    unmatched_test, unmatched_fe:
        Row indices that could not be matched: test channels absent from the
        model (a setup error unless intentionally tolerated) and FE DOFs that
        are simply not instrumented.
    labels:
        Optional label per shared DOF, for reports and COMAC plots.
    """

    test: npt.NDArray[Any]
    fe: npt.NDArray[Any]
    test_rows: npt.NDArray[np.intp]
    fe_rows: npt.NDArray[np.intp]
    unmatched_test: npt.NDArray[np.intp]
    unmatched_fe: npt.NDArray[np.intp]
    labels: tuple[str, ...] | None = None

    @property
    def n_dof(self) -> int:
        """Number of shared (correlation) DOFs."""
        return int(self.test.shape[0])

    def __repr__(self) -> str:
        return (
            f"AlignedShapes(n_dof={self.n_dof}, test_modes={self.test.shape[1]}, "
            f"fe_modes={self.fe.shape[1]}, unmatched_test={self.unmatched_test.size}, "
            f"unmatched_fe={self.unmatched_fe.size})"
        )


def selection_matrix(
    ndof: int,
    rows: Sequence[int] | npt.NDArray[np.intp],
    signs: Sequence[float] | npt.NDArray[np.float64] | None = None,
) -> npt.NDArray[np.float64]:
    """Dense ``(s, ndof)`` selection operator ``T`` picking ``rows``.

    ``signs`` flips channels whose measurement axis opposes the model axis.
    Reduction is normally done by fancy indexing; ``T`` is provided because
    weighted metrics and Guyan reduction need the operator itself.
    """
    idx = np.asarray(rows, dtype=np.intp).ravel()
    if idx.size and (idx.min() < 0 or idx.max() >= ndof):
        raise IndexError(f"row indices out of range for {ndof} DOFs")
    values = np.ones(idx.size) if signs is None else np.asarray(signs, dtype=float).ravel()
    if values.size != idx.size:
        raise ValueError("signs must have one entry per selected row")
    operator = np.zeros((idx.size, ndof))
    operator[np.arange(idx.size), idx] = values
    return operator


def align_dof_maps(
    fe_map: DofMap,
    test_map: DofMap,
    *,
    strict: bool = True,
) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.intp]]:
    """Row indices ``(fe_rows, test_rows)`` of the DOFs shared by two maps.

    The shared DOFs come back in *test* order, so a reduced FE shape lines up
    row by row with the measured shape.

    Raises
    ------
    KeyError
        With ``strict`` (the default) when a test channel has no counterpart
        in the model — silently dropping sensors hides instrumentation errors.
    """
    test_rows, fe_rows = test_map.intersection_indices(fe_map)
    if strict and test_rows.size != test_map.ndof:
        missing = sorted(set(range(test_map.ndof)) - set(test_rows.tolist()))
        node_ids = test_map.node_ids
        dof_types = test_map.dof_types
        detail = [(int(node_ids[i]), int(dof_types[i])) for i in missing]
        raise KeyError(f"test DOFs absent from the model (node_id, dof_type): {detail}")
    return np.asarray(fe_rows, dtype=np.intp), np.asarray(test_rows, dtype=np.intp)


def align_shapes(
    fe_shapes: Any,
    fe_map: DofMap,
    test_shapes: Any,
    test_map: DofMap,
    *,
    strict: bool = True,
) -> AlignedShapes:
    """Reduce FE and test shape matrices onto the DOFs their maps share."""
    fe = as_columns(fe_shapes, "fe_shapes")
    test = as_columns(test_shapes, "test_shapes")
    if fe.shape[0] != fe_map.ndof:
        raise ValueError(f"fe_shapes has {fe.shape[0]} rows but the map has {fe_map.ndof} DOFs")
    if test.shape[0] != test_map.ndof:
        raise ValueError(
            f"test_shapes has {test.shape[0]} rows but the map has {test_map.ndof} DOFs"
        )
    fe_rows, test_rows = align_dof_maps(fe_map, test_map, strict=strict)
    if fe_rows.size == 0:
        raise ValueError("the FE and test DOF maps share no DOF; correlation is impossible")
    node_ids = test_map.node_ids
    dof_types = test_map.dof_types
    labels = tuple(f"{int(node_ids[i])}:{int(dof_types[i])}" for i in test_rows)
    return AlignedShapes(
        test=test[test_rows, :],
        fe=fe[fe_rows, :],
        test_rows=test_rows,
        fe_rows=fe_rows,
        unmatched_test=np.setdiff1d(np.arange(test_map.ndof, dtype=np.intp), test_rows),
        unmatched_fe=np.setdiff1d(np.arange(fe_map.ndof, dtype=np.intp), fe_rows),
        labels=labels,
    )


def align_modal_data(
    fe_result: HasShapesAndDofMap,
    test_data: HasShapesAndDofMap,
    *,
    strict: bool = True,
) -> AlignedShapes:
    """Align a :class:`ModalResult` with a :class:`TestData` through their maps."""
    return align_shapes(
        fe_result.shapes,
        fe_result.dof_map,
        test_data.shapes,
        test_data.dof_map,
        strict=strict,
    )


def align_by_labels(
    fe_shapes: Any,
    fe_labels: Sequence[str],
    test_shapes: Any,
    test_labels: Sequence[str],
    *,
    signs: Sequence[float] | None = None,
    strict: bool = True,
) -> AlignedShapes:
    """Align two shape sets whose rows are identified by string DOF labels.

    Parameters
    ----------
    signs:
        Optional orientation sign per test channel (``+1``/``-1``), applied to
        the measured shapes so both sets use the model's axis convention.
    strict:
        Raise on test channels missing from the model instead of dropping them.
    """
    fe = as_columns(fe_shapes, "fe_shapes")
    test = as_columns(test_shapes, "test_shapes")
    fe_names = [str(label) for label in fe_labels]
    test_names = [str(label) for label in test_labels]
    if len(set(fe_names)) != len(fe_names):
        raise ValueError("fe_labels must be unique")
    if len(set(test_names)) != len(test_names):
        raise ValueError("test_labels must be unique")
    if fe.shape[0] != len(fe_names):
        raise ValueError(f"fe_shapes has {fe.shape[0]} rows but {len(fe_names)} labels")
    if test.shape[0] != len(test_names):
        raise ValueError(f"test_shapes has {test.shape[0]} rows but {len(test_names)} labels")

    fe_index = {label: row for row, label in enumerate(fe_names)}
    missing = [label for label in test_names if label not in fe_index]
    if missing and strict:
        raise KeyError(f"test DOFs absent from the model: {missing}")

    test_rows = np.array(
        [i for i, label in enumerate(test_names) if label in fe_index], dtype=np.intp
    )
    fe_rows = np.array([fe_index[test_names[i]] for i in test_rows], dtype=np.intp)
    if fe_rows.size == 0:
        raise ValueError("the FE and test label sets share no DOF; correlation is impossible")

    reduced_test = test[test_rows, :]
    if signs is not None:
        orientation = np.asarray(signs, dtype=float).ravel()
        if orientation.size != len(test_names):
            raise ValueError("signs must have one entry per test DOF")
        reduced_test = reduced_test * orientation[test_rows, None]

    return AlignedShapes(
        test=reduced_test,
        fe=fe[fe_rows, :],
        test_rows=test_rows,
        fe_rows=fe_rows,
        unmatched_test=np.setdiff1d(np.arange(len(test_names), dtype=np.intp), test_rows),
        unmatched_fe=np.setdiff1d(np.arange(len(fe_names), dtype=np.intp), fe_rows),
        labels=tuple(test_names[i] for i in test_rows),
    )
