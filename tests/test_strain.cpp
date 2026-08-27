#include <cmath>

#include "dic/correlation.hpp"
#include "dic/image.hpp"
#include "dic/strain.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  const int W = 320, H = 320;
  Image ref = makeSpeckle(W, H, 18000, 1.2, 99u);

  // Uniform strain field: exx = 0.012, eyy = -0.008, shear exy = 0.005.
  AffineField field;
  field.center = {W / 2.0, H / 2.0};
  field.t = {0.4, -0.3};
  field.A = {{{{0.012, 0.005}}, {{0.005, -0.008}}}};
  Image def = warpAffine(ref, field);

  DICOptions opt;
  opt.icgn.subsetRadius = 18;
  opt.step = 10;
  opt.searchRadius = 6;
  opt.znccThreshold = 0.9;
  opt.pathIndependent = true;

  ROI roi{0, 0, W - 1, H - 1};
  DICField f = correlate(ref, def, roi, opt);
  StrainField sf = computeStrain(f, 2);

  int n = 0;
  double sExx = 0, sEyy = 0, sExy = 0;
  for (const StrainPoint& p : sf.points) {
    if (!p.valid) continue;
    ++n;
    sExx += p.Exx;
    sEyy += p.Eyy;
    sExy += p.Exy;
  }
  CHECK(n > 0);
  const double mExx = sExx / n, mEyy = sEyy / n, mExy = sExy / n;

  // Green-Lagrange of the prescribed uniform field (F = I + A).
  const double a00 = 0.012, a01 = 0.005, a10 = 0.005, a11 = -0.008;
  const double gExx = a00 + 0.5 * (a00 * a00 + a10 * a10);
  const double gEyy = a11 + 0.5 * (a01 * a01 + a11 * a11);
  const double gExy = 0.5 * (a01 + a10) + 0.5 * (a00 * a01 + a10 * a11);

  std::printf("strain measured: Exx=%.5f Eyy=%.5f Exy=%.5f  truth: %.5f %.5f %.5f (n=%d)\n",
              mExx, mEyy, mExy, gExx, gEyy, gExy, n);

  CHECK_NEAR(mExx, gExx, 1e-3);
  CHECK_NEAR(mEyy, gEyy, 1e-3);
  CHECK_NEAR(mExy, gExy, 1e-3);

  TEST_REPORT();
}
