#include <cmath>

#include "dic/icgn.hpp"
#include "dic/image.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

// Honest sub-pixel bias assessment WITHOUT an "inverse crime": the deformed
// image is the analytic Gaussian-sum pattern rasterized at shifted speckle
// centers (an exact rigid translation), so it does not pass through the same
// bicubic the matcher uses. This measures the true interpolation-bias floor.
int main() {
  const int W = 180, H = 180;
  const SpecklePattern pattern = makeSpecklePattern(W, H, 6000, 1.3, 555u);
  const Image ref = renderPattern(pattern, W, H, 0.0, 0.0);

  ICGNOptions opt;
  opt.subsetRadius = 20;
  opt.maxIterations = 60;
  opt.convergenceTol = 1e-5;

  double maxBias = 0.0, sumSq = 0.0;
  int count = 0;
  std::printf("shift  measured   bias\n");
  for (int k = 0; k <= 10; ++k) {
    const double s = 0.1 * k;
    const Image def = renderPattern(pattern, W, H, s, 0.0);
    Params init;
    init.u = std::round(s);
    const ICGNResult res = icgnMatch(ref, def, W / 2, H / 2, init, opt);
    const double err = res.params.u - s;
    std::printf("%.1f    %+.4f    %+.4f\n", s, res.params.u, err);
    CHECK(res.converged);
    maxBias = std::max(maxBias, std::fabs(err));
    sumSq += err * err;
    ++count;
  }
  const double rms = std::sqrt(sumSq / count);
  std::printf("HONEST (analytic rendering) max |bias| = %.4f px   RMS = %.4f px\n",
              maxBias, rms);

  // Documents the true Keys-bicubic interpolation-bias floor (~0.017 px peak).
  // The biquintic B-spline milestone targets an order-of-magnitude reduction.
  CHECK(maxBias < 0.03);

  TEST_REPORT();
}
