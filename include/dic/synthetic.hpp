#pragma once

#include <array>
#include <cstdint>

#include "dic/image.hpp"

namespace dic {

// Generate a random Gaussian-speckle pattern suitable for correlation.
Image makeSpeckle(int width, int height, int numSpeckles, double speckleSigma,
                  uint32_t seed, double background = 20.0, double amplitude = 220.0);

// Affine displacement field about a center, expressed in reference coordinates:
//   u(X) = A * (X - center) + t
// where A = [[a00, a01], [a10, a11]] and t = [tx, ty].
struct AffineField {
  std::array<std::array<double, 2>, 2> A{{{{0.0, 0.0}}, {{0.0, 0.0}}}};
  std::array<double, 2> t{{0.0, 0.0}};
  std::array<double, 2> center{{0.0, 0.0}};

  void displacement(double x, double y, double& u, double& v) const {
    const double dx = x - center[0];
    const double dy = y - center[1];
    u = A[0][0] * dx + A[0][1] * dy + t[0];
    v = A[1][0] * dx + A[1][1] * dy + t[1];
  }
};

// Produce a deformed image from a reference image under an affine field, using
// exact backward mapping g(p) = f(X) with X + u(X) = p and bicubic sampling.
Image warpAffine(const Image& ref, const AffineField& field);

}  // namespace dic
