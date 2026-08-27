#pragma once

#include "dic/image.hpp"
#include "dic/shape_function.hpp"
#include "dic/spline.hpp"

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

// Same IC-GN/ZNSSD solver, but sampling both images through prefiltered cubic
// B-splines: the deformed intensities and the reference steepest-descent
// gradients come from the same spline model (lower interpolation bias, and
// gradients consistent with the interpolant).
ICGNResult icgnMatchSpline(const BSplineImage& ref, const BSplineImage& def,
                           int x0, int y0, const Params& init,
                           const ICGNOptions& opt);

}  // namespace dic
