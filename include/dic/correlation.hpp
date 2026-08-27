#pragma once

#include <cstddef>
#include <vector>

#include "dic/icgn.hpp"
#include "dic/image.hpp"

namespace dic {

struct ROI {
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;  // inclusive pixel bounds
};

struct DICOptions {
  ICGNOptions icgn;
  int step = 5;                // grid spacing in pixels
  int searchRadius = 8;        // integer initial-guess search range (pixels)
  double znccThreshold = 0.8;  // minimum ZNCC to accept a point
  // When true, every point is solved independently from its own integer-pixel
  // ZNCC search, enabling OpenMP parallelism (path-independent DIC). When
  // false, a single seed is refined and its solution is propagated across
  // neighbors in ZNCC-priority order (reliability-guided DIC).
  bool pathIndependent = false;
};

struct POI {
  int x = 0, y = 0;  // reference pixel location
  Params params;
  double zncc = -1.0;
  int iterations = 0;
  bool valid = false;
};

struct DICField {
  int cols = 0, rows = 0;
  int step = 0;
  std::vector<POI> points;  // row-major, size cols*rows

  const POI& at(int c, int r) const { return points[static_cast<size_t>(r) * cols + c]; }
  POI& at(int c, int r) { return points[static_cast<size_t>(r) * cols + c]; }
};

// Full-field correlation over a grid of points using an integer-pixel seed
// followed by reliability-guided (ZNCC-ordered) propagation of the IC-GN
// solver across neighbors.
DICField correlate(const Image& ref, const Image& def, const ROI& roi,
                   const DICOptions& opt);

}  // namespace dic
