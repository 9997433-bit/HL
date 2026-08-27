#include <cmath>

#include "dic/icgn.hpp"
#include "dic/image.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

// Sub-pixel bias assessment: impose known fractional translations and measure
// the systematic error of the recovered displacement (the interpolation-bias
// floor of the correlator).
int main() {
  const int W = 200, H = 200;
  Image ref = makeSpeckle(W, H, 9000, 1.3, 555u);

  ICGNOptions opt;
  opt.subsetRadius = 20;
  opt.maxIterations = 60;
  opt.convergenceTol = 1e-5;

  double maxBias = 0.0, sumSq = 0.0;
  int count = 0;
  std::printf("shift  measured   error\n");
  for (int k = 0; k <= 10; ++k) {
    const double s = 0.1 * k;
    AffineField field;
    field.center = {W / 2.0, H / 2.0};
    field.t = {s, 0.0};
    Image def = warpAffine(ref, field);

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
  std::printf("max |bias| = %.4f px   RMS bias = %.4f px\n", maxBias, rms);

  // Keys bicubic bias floor; motivates the B-spline interpolation milestone.
  CHECK(maxBias < 0.02);
  CHECK(rms < 0.01);

  TEST_REPORT();
}
