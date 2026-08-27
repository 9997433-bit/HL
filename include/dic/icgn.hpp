#pragma once

#include "dic/image.hpp"
#include "dic/shape_function.hpp"

namespace dic {

struct ICGNOptions {
  int subsetRadius = 15;       // half-width of the square subset, in pixels
  int maxIterations = 50;
  double convergenceTol = 1e-4;  // on incremental warp of the subset corner
};

struct ICGNResult {
  Params params;
  double zncc = -1.0;   // zero-normalized cross-correlation coefficient [-1, 1]
  int iterations = 0;
  bool converged = false;
};

// Refine the affine warp aligning the reference subset centered at integer
// pixel (x0, y0) with the deformed image, using the inverse-compositional
// Gauss-Newton algorithm minimizing the ZNSSD criterion.
ICGNResult icgnMatch(const Image& ref, const Image& def, int x0, int y0,
                     const Params& init, const ICGNOptions& opt);

}  // namespace dic
