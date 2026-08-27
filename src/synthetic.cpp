#include "dic/synthetic.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <random>

#include "dic/interpolation.hpp"

namespace dic {

Image makeSpeckle(int width, int height, int numSpeckles, double speckleSigma,
                  uint32_t seed, double background, double amplitude) {
  Image img(width, height);
  for (double& v : img.data) v = background;

  std::mt19937 rng(seed);
  std::uniform_real_distribution<double> ux(0.0, width - 1.0);
  std::uniform_real_distribution<double> uy(0.0, height - 1.0);
  std::uniform_real_distribution<double> ur(0.75, 1.25);

  const int radius = std::max(1, static_cast<int>(std::ceil(3.0 * speckleSigma)));
  for (int s = 0; s < numSpeckles; ++s) {
    const double cx = ux(rng);
    const double cy = uy(rng);
    const double sigma = speckleSigma * ur(rng);
    const double inv2s2 = 1.0 / (2.0 * sigma * sigma);
    const int x0 = std::max(0, static_cast<int>(cx) - radius);
    const int x1 = std::min(width - 1, static_cast<int>(cx) + radius);
    const int y0 = std::max(0, static_cast<int>(cy) - radius);
    const int y1 = std::min(height - 1, static_cast<int>(cy) + radius);
    for (int y = y0; y <= y1; ++y)
      for (int x = x0; x <= x1; ++x) {
        const double dx = x - cx, dy = y - cy;
        img.at(x, y) += amplitude * std::exp(-(dx * dx + dy * dy) * inv2s2);
      }
  }
  for (double& v : img.data) v = std::clamp(v, 0.0, 255.0);
  return img;
}

Image warpAffine(const Image& ref, const AffineField& field) {
  // Deformed pixel p maps back to reference X with X + u(X) = p.
  // For u(X) = A (X - c) + t this is affine in X:
  //   p - c = (I + A)(X - c) + t  =>  X - c = (I + A)^{-1} (p - c - t)
  const double a = 1.0 + field.A[0][0];
  const double b = field.A[0][1];
  const double cc = field.A[1][0];
  const double d = 1.0 + field.A[1][1];
  const double det = a * d - b * cc;
  const double ia = d / det, ib = -b / det, ic = -cc / det, id = a / det;

  Image out(ref.width, ref.height);
  for (int y = 0; y < ref.height; ++y)
    for (int x = 0; x < ref.width; ++x) {
      const double px = x - field.center[0] - field.t[0];
      const double py = y - field.center[1] - field.t[1];
      const double rx = ia * px + ib * py + field.center[0];
      const double ry = ic * px + id * py + field.center[1];
      out.at(x, y) = bicubic(ref, rx, ry);
    }
  return out;
}

Image warpField(const Image& ref,
                const std::function<void(double, double, double&, double&)>& disp) {
  Image out(ref.width, ref.height);
  for (int y = 0; y < ref.height; ++y)
    for (int x = 0; x < ref.width; ++x) {
      // Solve X + u(X) = p by fixed-point iteration X <- p - u(X).
      double rx = x, ry = y;
      for (int it = 0; it < 20; ++it) {
        double u, v;
        disp(rx, ry, u, v);
        const double nx = x - u, ny = y - v;
        if (std::fabs(nx - rx) < 1e-6 && std::fabs(ny - ry) < 1e-6) {
          rx = nx;
          ry = ny;
          break;
        }
        rx = nx;
        ry = ny;
      }
      out.at(x, y) = bicubic(ref, rx, ry);
    }
  return out;
}

}  // namespace dic
