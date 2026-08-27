#pragma once

#include <array>
#include <cstdint>
#include <functional>

#include "dic/image.hpp"

namespace dic {

// A closed-form Gaussian-sum speckle pattern. Because the pattern is analytic,
// a translated version can be rendered *exactly* by rasterizing the speckles at
// shifted centers, with no image interpolation in the generation path. This is
// what makes bias measurements free of the "inverse crime" (the estimator and
// the forward model no longer share an interpolant).
struct Speckle {
  double cx, cy, amp, sigma;
};
struct SpecklePattern {
  std::vector<Speckle> speckles;
  double background = 20.0;
  double baseSigma = 1.2;

  // Continuous intensity of the (undeformed) pattern at real coordinates.
  double eval(double x, double y) const;
};

// Build a random speckle pattern (deterministic in seed).
SpecklePattern makeSpecklePattern(int width, int height, int numSpeckles,
                                  double speckleSigma, uint32_t seed,
                                  double background = 20.0, double amplitude = 220.0);

// Rasterize the pattern with all speckle centers shifted by (offX, offY). With
// offset (0,0) this is the reference; with (s, 0) it is an exact rigid
// translation by s of the continuous pattern.
Image renderPattern(const SpecklePattern& pattern, int width, int height,
                    double offX, double offY);

// Generate a random Gaussian-speckle pattern suitable for correlation
// (equivalent to renderPattern(makeSpecklePattern(...), w, h, 0, 0)).
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

// Analytic (inverse-crime-free) affine deformation: the deformed image is the
// continuous pattern evaluated at the back-mapped coordinate, with no image
// interpolation in the generation path.
Image renderAffine(const SpecklePattern& pattern, int width, int height,
                   const AffineField& field);

// Produce a deformed image under an arbitrary (reference-coordinate)
// displacement field disp(x, y) -> (u, v). The backward mapping X + u(X) = p is
// solved by fixed-point iteration (valid for smooth, small-gradient fields).
Image warpField(const Image& ref,
                const std::function<void(double, double, double&, double&)>& disp);

}  // namespace dic
