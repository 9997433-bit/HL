use numpy::{PyArray1, PyReadonlyArray2, PyUntypedArrayMethods};
use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyfunction]
fn assemble_rod2_stiffness<'py>(
    py: Python<'py>,
    node_coords: PyReadonlyArray2<'py, f64>,
    connectivity: PyReadonlyArray2<'py, i64>,
    axial_stiffness: PyReadonlyArray2<'py, f64>,
    dof_indices: PyReadonlyArray2<'py, i64>,
) -> PyResult<(
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<f64>>,
)> {
    let coords = node_coords.as_array();
    let elems = connectivity.as_array();
    let stiffness = axial_stiffness.as_array();
    let dofs = dof_indices.as_array();
    let n_elem = elems.nrows();
    let mut rows = Vec::with_capacity(16 * n_elem);
    let mut cols = Vec::with_capacity(16 * n_elem);
    let mut data = Vec::with_capacity(16 * n_elem);

    for e in 0..n_elem {
        let n1 = elems[[e, 0]] as usize;
        let n2 = elems[[e, 1]] as usize;
        let dx = coords[[n2, 0]] - coords[[n1, 0]];
        let dy = coords[[n2, 1]] - coords[[n1, 1]];
        let dz = coords[[n2, 2]] - coords[[n1, 2]];
        let length = (dx * dx + dy * dy + dz * dz).sqrt();
        if length <= 0.0 {
            continue;
        }
        let c = dx / length;
        let s1 = dy / length;
        let s2 = dz / length;
        let k = stiffness[[e, 0]] / length;
        let local = [
            [c * c, c * s1, c * s2, -c * c, -c * s1, -c * s2],
            [c * s1, s1 * s1, s1 * s2, -c * s1, -s1 * s1, -s1 * s2],
            [c * s2, s1 * s2, s2 * s2, -c * s2, -s1 * s2, -s2 * s2],
            [-c * c, -c * s1, -c * s2, c * c, c * s1, c * s2],
            [-c * s1, -s1 * s1, -s1 * s2, c * s1, s1 * s1, s1 * s2],
            [-c * s2, -s1 * s2, -s2 * s2, c * s2, s1 * s2, s2 * s2],
        ];
        let elem_dofs = [
            dofs[[n1, 0]],
            dofs[[n1, 1]],
            dofs[[n1, 2]],
            dofs[[n2, 0]],
            dofs[[n2, 1]],
            dofs[[n2, 2]],
        ];
        for i in 0..6 {
            for j in 0..6 {
                let value = k * local[i][j];
                if value == 0.0 {
                    continue;
                }
                rows.push(elem_dofs[i]);
                cols.push(elem_dofs[j]);
                data.push(value);
            }
        }
    }

    Ok((
        PyArray1::from_vec_bound(py, rows),
        PyArray1::from_vec_bound(py, cols),
        PyArray1::from_vec_bound(py, data),
    ))
}

#[pymodule]
fn openfemlab_asm(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(assemble_rod2_stiffness, m)?)?;
    Ok(())
}
