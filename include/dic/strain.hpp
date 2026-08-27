#pragma once

#include <cstddef>
#include <vector>

#include "dic/correlation.hpp"

namespace dic {

struct StrainPoint {
  // Displacement-gradient tensor components (dimensionless).
  double dudx = 0, dudy = 0, dvdx = 0, dvdy = 0;
  // Green-Lagrange strain tensor.
  double Exx = 0, Eyy = 0, Exy = 0;
  bool valid = false;
};

struct StrainField {
  int cols = 0, rows = 0;
  std::vector<StrainPoint> points;  // row-major, aligned with the DICField grid

  const StrainPoint& at(int c, int r) const { return points[static_cast<size_t>(r) * cols + c]; }
  StrainPoint& at(int c, int r) { return points[static_cast<size_t>(r) * cols + c]; }
};

// Compute strain from a displacement field using a pointwise least-squares
// (PLS) plane fit of u and v over a local window (radius in grid steps), then
// the Green-Lagrange tensor E = 1/2 (F^T F - I), F = I + grad(displacement).
StrainField computeStrain(const DICField& field, int windowRadius);

}  // namespace dic
