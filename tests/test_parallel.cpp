#include <chrono>
#include <cmath>

#include "dic/correlation.hpp"
#include "dic/image.hpp"
#include "dic/synthetic.hpp"
#include "test_util.hpp"

using namespace dic;

namespace {

double rmsError(const DICField& f, const AffineField& field, int& valid) {
  valid = 0;
  double s = 0.0;
  for (const POI& p : f.points) {
    if (!p.valid) continue;
    ++valid;
    double ugt, vgt;
    field.displacement(p.x, p.y, ugt, vgt);
    const double eu = p.params.u - ugt, ev = p.params.v - vgt;
    s += eu * eu + ev * ev;
  }
  return std::sqrt(s / std::max(valid, 1));
}

}  // namespace

int main() {
  const int W = 384, H = 384;
  Image ref = makeSpeckle(W, H, 25000, 1.2, 321u);
  AffineField field;
  field.center = {W / 2.0, H / 2.0};
  field.t = {0.55, -0.35};
  field.A = {{{{0.007, 0.001}}, {{0.0015, -0.005}}}};
  Image def = warpAffine(ref, field);

  DICOptions base;
  base.icgn.subsetRadius = 18;
  base.step = 8;
  base.searchRadius = 6;
  base.znccThreshold = 0.9;
  ROI roi{0, 0, W - 1, H - 1};

  DICOptions seq = base;
  seq.pathIndependent = false;
  DICOptions par = base;
  par.pathIndependent = true;

  auto t0 = std::chrono::steady_clock::now();
  DICField fSeq = correlate(ref, def, roi, seq);
  auto t1 = std::chrono::steady_clock::now();
  DICField fPar = correlate(ref, def, roi, par);
  auto t2 = std::chrono::steady_clock::now();

  int vSeq = 0, vPar = 0;
  const double rmsSeq = rmsError(fSeq, field, vSeq);
  const double rmsPar = rmsError(fPar, field, vPar);

  const double msSeq = std::chrono::duration<double, std::milli>(t1 - t0).count();
  const double msPar = std::chrono::duration<double, std::milli>(t2 - t1).count();
  std::printf("reliability-guided: rms=%.4f px valid=%d  (%.1f ms)\n", rmsSeq, vSeq, msSeq);
  std::printf("path-independent  : rms=%.4f px valid=%d  (%.1f ms)\n", rmsPar, vPar, msPar);

  // Both modes must reach the same (sub-pixel) accuracy on the full field.
  CHECK(rmsSeq < 0.02);
  CHECK(rmsPar < 0.02);
  CHECK(vSeq > 0 && vPar > 0);
  CHECK(std::fabs(rmsSeq - rmsPar) < 0.01);

  TEST_REPORT();
}
