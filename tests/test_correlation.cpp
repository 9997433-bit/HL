#include <cmath>

#include "dic/correlation.hpp"
#include "dic/image.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  const int W = 320, H = 320;
  Image ref = makeSpeckle(W, H, 18000, 1.2, 2024u);

  AffineField field;
  field.center = {W / 2.0, H / 2.0};
  field.t = {0.63, -0.41};
  field.A = {{{{0.006, 0.001}}, {{0.002, -0.004}}}};
  Image def = warpAffine(ref, field);

  DICOptions opt;
  opt.icgn.subsetRadius = 18;
  opt.icgn.maxIterations = 50;
  opt.icgn.convergenceTol = 1e-4;
  opt.step = 10;
  opt.searchRadius = 6;
  opt.znccThreshold = 0.9;

  ROI roi{0, 0, W - 1, H - 1};
  DICField f = correlate(ref, def, roi, opt);

  int valid = 0, total = 0;
  double sumSqU = 0.0, sumSqV = 0.0, maxErr = 0.0, sumZncc = 0.0;
  for (const POI& p : f.points) {
    ++total;
    if (!p.valid) continue;
    ++valid;
    double ugt, vgt;
    field.displacement(p.x, p.y, ugt, vgt);
    const double eu = p.params.u - ugt;
    const double ev = p.params.v - vgt;
    sumSqU += eu * eu;
    sumSqV += ev * ev;
    maxErr = std::max(maxErr, std::sqrt(eu * eu + ev * ev));
    sumZncc += p.zncc;
  }
  CHECK(valid > 0);
  const double rmsU = std::sqrt(sumSqU / valid);
  const double rmsV = std::sqrt(sumSqV / valid);
  const double meanZncc = sumZncc / valid;
  const double validFrac = static_cast<double>(valid) / total;

  std::printf("valid=%d/%d (%.1f%%) rmsU=%.4f px rmsV=%.4f px maxErr=%.4f px meanZNCC=%.5f\n",
              valid, total, 100.0 * validFrac, rmsU, rmsV, maxErr, meanZncc);

  CHECK(validFrac > 0.9);
  CHECK(rmsU < 0.02);
  CHECK(rmsV < 0.02);
  CHECK(maxErr < 0.1);
  CHECK(meanZncc > 0.99);

  TEST_REPORT();
}
