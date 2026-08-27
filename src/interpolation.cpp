#include "dic/interpolation.hpp"

#include <algorithm>
#include <cmath>

namespace dic {

namespace {

// Keys bicubic convolution kernel with a = -0.5 (interpolating, C1, partition
// of unity), giving third-order accuracy for smooth signals.
inline double cubicKernel(double t) {
  const double a = -0.5;
  t = std::fabs(t);
  if (t <= 1.0) return ((a + 2.0) * t - (a + 3.0)) * t * t + 1.0;
  if (t < 2.0) return (((a * t - 5.0 * a) * t + 8.0 * a) * t - 4.0 * a);
  return 0.0;
}

inline int clampIndex(int v, int hi) { return std::clamp(v, 0, hi); }

}  // namespace

double bicubic(const Image& img, double x, double y) {
  const int ix = static_cast<int>(std::floor(x));
  const int iy = static_cast<int>(std::floor(y));
  const double fx = x - ix;
  const double fy = y - iy;

  double wx[4], wy[4];
  for (int m = -1; m <= 2; ++m) {
    wx[m + 1] = cubicKernel(fx - m);
    wy[m + 1] = cubicKernel(fy - m);
  }

  double value = 0.0;
  for (int n = -1; n <= 2; ++n) {
    const int yy = clampIndex(iy + n, img.height - 1);
    double row = 0.0;
    for (int m = -1; m <= 2; ++m) {
      const int xx = clampIndex(ix + m, img.width - 1);
      row += img.at(xx, yy) * wx[m + 1];
    }
    value += row * wy[n + 1];
  }
  return value;
}

double gradX(const Image& img, int x, int y) {
  const int xm = std::max(x - 1, 0);
  const int xp = std::min(x + 1, img.width - 1);
  return 0.5 * (img.at(xp, y) - img.at(xm, y));
}

double gradY(const Image& img, int x, int y) {
  const int ym = std::max(y - 1, 0);
  const int yp = std::min(y + 1, img.height - 1);
  return 0.5 * (img.at(x, yp) - img.at(x, ym));
}

}  // namespace dic
