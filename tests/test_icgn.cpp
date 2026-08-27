#include <cmath>

#include "dic/icgn.hpp"
#include "dic/image.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  const int W = 160, H = 160;
  Image ref = makeSpeckle(W, H, 5000, 1.3, 12345u);

  // Pure sub-pixel translation.
  AffineField field;
  field.center = {W / 2.0, H / 2.0};
  field.t = {1.37, -0.72};
  Image def = warpAffine(ref, field);

  ICGNOptions opt;
  opt.subsetRadius = 20;
  opt.maxIterations = 60;
  opt.convergenceTol = 1e-5;

  Params init;
  init.u = 1.0;  // integer-level initial guess
  init.v = -1.0;
  const ICGNResult res = icgnMatch(ref, def, W / 2, H / 2, init, opt);

  std::printf("translation: u=%.4f v=%.4f zncc=%.5f iters=%d\n", res.params.u,
              res.params.v, res.zncc, res.iterations);
  CHECK(res.converged);
  CHECK(res.zncc > 0.98);
  CHECK_NEAR(res.params.u, 1.37, 0.02);
  CHECK_NEAR(res.params.v, -0.72, 0.02);

  // Translation plus a small uniform strain (exercises the affine terms).
  AffineField field2;
  field2.center = {W / 2.0, H / 2.0};
  field2.t = {0.5, 0.3};
  field2.A = {{{{0.01, 0.0}}, {{0.0, -0.008}}}};
  Image def2 = warpAffine(ref, field2);

  Params init2;
  init2.u = 1.0;
  init2.v = 0.0;
  const ICGNResult res2 = icgnMatch(ref, def2, W / 2, H / 2, init2, opt);
  std::printf("affine: u=%.4f v=%.4f exx=%.5f eyy=%.5f zncc=%.5f iters=%d\n",
              res2.params.u, res2.params.v, res2.params.ux, res2.params.vy,
              res2.zncc, res2.iterations);
  CHECK(res2.converged);
  CHECK(res2.zncc > 0.98);
  CHECK_NEAR(res2.params.u, 0.5, 0.03);
  CHECK_NEAR(res2.params.v, 0.3, 0.03);
  CHECK_NEAR(res2.params.ux, 0.01, 0.003);
  CHECK_NEAR(res2.params.vy, -0.008, 0.003);

  TEST_REPORT();
}
