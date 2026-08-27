#include <cmath>

#include "dic/image.hpp"
#include "dic/spline.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  const int W = 48, H = 48;

  // Interpolation property: at integer nodes the spline reproduces the samples.
  Image r(W, H);
  for (int y = 0; y < H; ++y)
    for (int x = 0; x < W; ++x)
      r.at(x, y) = 40.0 + 30.0 * std::sin(0.3 * x) * std::cos(0.25 * y);
  BSplineImage sp(r);
  for (int y = 8; y < H - 8; ++y)
    for (int x = 8; x < W - 8; ++x) CHECK_NEAR(sp.eval(x, y), r.at(x, y), 1e-6);

  // Cubic B-splines reproduce cubic polynomials exactly (interior).
  Image cubic(W, H);
  auto fc = [](double x, double y) {
    return 1.0 + 0.5 * x - 0.3 * y + 0.02 * x * x - 0.01 * x * y + 0.001 * x * x * x;
  };
  for (int y = 0; y < H; ++y)
    for (int x = 0; x < W; ++x) cubic.at(x, y) = fc(x, y);
  BSplineImage spc(cubic);
  CHECK_NEAR(spc.eval(24.3, 20.7), fc(24.3, 20.7), 1e-3);
  CHECK_NEAR(spc.eval(18.5, 27.25), fc(18.5, 27.25), 1e-3);

  // Analytic gradient agrees with a central finite difference (interior).
  double v, gx, gy;
  spc.evalGrad(24.3, 20.7, v, gx, gy);
  const double h = 1e-3;
  const double fdX = (spc.eval(24.3 + h, 20.7) - spc.eval(24.3 - h, 20.7)) / (2 * h);
  const double fdY = (spc.eval(24.3, 20.7 + h) - spc.eval(24.3, 20.7 - h)) / (2 * h);
  CHECK_NEAR(gx, fdX, 1e-4);
  CHECK_NEAR(gy, fdY, 1e-4);

  TEST_REPORT();
}
