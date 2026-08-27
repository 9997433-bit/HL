#include <cmath>

#include "dic/icgn.hpp"
#include "dic/image.hpp"
#include "dic/spline.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

// Honest sub-pixel bias assessment WITHOUT an "inverse crime": the deformed
// image is the analytic Gaussian-sum pattern rasterized at shifted speckle
// centers (an exact rigid translation), so it does not pass through the same
// bicubic the matcher uses. This measures the true interpolation-bias floor.
int main() {
  const int W = 180, H = 180;
  // Non-saturating, realistically-sized speckle (~4 px): summed intensity stays
  // within [0, 255] so the continuous pattern is smooth (no clipping kinks that
  // would make any interpolator ring).
  const SpecklePattern pattern = makeSpecklePattern(W, H, 1000, 2.0, 555u, 25.0, 60.0);
  const Image ref = renderPattern(pattern, W, H, 0.0, 0.0);

  ICGNOptions opt;
  opt.subsetRadius = 20;
  opt.maxIterations = 60;
  opt.convergenceTol = 1e-5;

  const BSplineImage refS(ref);

  double maxKeys = 0.0, sqKeys = 0.0, maxSpline = 0.0, sqSpline = 0.0;
  int count = 0;
  std::printf("shift   Keys-bias   Bspline-bias\n");
  for (int k = 0; k <= 10; ++k) {
    const double s = 0.1 * k;
    const Image def = renderPattern(pattern, W, H, s, 0.0);
    const BSplineImage defS(def);
    Params init;
    init.u = std::round(s);

    const ICGNResult keys = icgnMatch(ref, def, W / 2, H / 2, init, opt);
    const ICGNResult spl = icgnMatchSpline(refS, defS, W / 2, H / 2, init, opt);
    const double eKeys = keys.params.u - s;
    const double eSpline = spl.params.u - s;
    std::printf("%.1f     %+.4f      %+.4f\n", s, eKeys, eSpline);
    CHECK(keys.converged);
    CHECK(spl.converged);
    maxKeys = std::max(maxKeys, std::fabs(eKeys));
    sqKeys += eKeys * eKeys;
    maxSpline = std::max(maxSpline, std::fabs(eSpline));
    sqSpline += eSpline * eSpline;
    ++count;
  }
  const double rmsKeys = std::sqrt(sqKeys / count);
  const double rmsSpline = std::sqrt(sqSpline / count);
  std::printf("Keys    : max |bias| = %.4f px  RMS = %.4f px\n", maxKeys, rmsKeys);
  std::printf("Bspline : max |bias| = %.4f px  RMS = %.4f px\n", maxSpline, rmsSpline);

  // Honest (no inverse-crime) sub-pixel bias. On a smooth, non-saturating
  // speckle the prefiltered cubic B-spline substantially reduces systematic
  // bias versus Keys convolution (the biquintic milestone pushes it lower yet).
  CHECK(maxKeys < 0.02);
  CHECK(maxSpline < maxKeys * 0.6);
  CHECK(rmsSpline < rmsKeys * 0.6);

  TEST_REPORT();
}
