#pragma once

#include <array>
#include <cmath>

namespace dic {

// First-order (affine) shape function parameters describing the mapping of a
// subset from the reference to the deformed image:
//   x' = x0 + dx + u  + ux*dx + uy*dy
//   y' = y0 + dy + v  + vx*dx + vy*dy
struct Params {
  double u = 0, ux = 0, uy = 0;
  double v = 0, vx = 0, vy = 0;
};

using Mat3 = std::array<std::array<double, 3>, 3>;

inline Mat3 warpMatrix(const Params& p) {
  return {{{{1.0 + p.ux, p.uy, p.u}},
           {{p.vx, 1.0 + p.vy, p.v}},
           {{0.0, 0.0, 1.0}}}};
}

inline Params paramsFromMatrix(const Mat3& W) {
  Params p;
  p.u = W[0][2];
  p.v = W[1][2];
  p.ux = W[0][0] - 1.0;
  p.uy = W[0][1];
  p.vx = W[1][0];
  p.vy = W[1][1] - 1.0;
  return p;
}

inline Mat3 matMul(const Mat3& A, const Mat3& B) {
  Mat3 C{};
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) {
      double s = 0.0;
      for (int k = 0; k < 3; ++k) s += A[i][k] * B[k][j];
      C[i][j] = s;
    }
  return C;
}

// Invert an affine 3x3 warp (last row [0 0 1]). Returns false if singular.
inline bool invertAffine(const Mat3& W, Mat3& inv) {
  const double a = W[0][0], b = W[0][1], c = W[1][0], d = W[1][1];
  const double det = a * d - b * c;
  if (std::fabs(det) < 1e-14) return false;
  const double ia = d / det, ib = -b / det, ic = -c / det, id = a / det;
  const double tx = W[0][2], ty = W[1][2];
  inv = {{{{ia, ib, -(ia * tx + ib * ty)}},
          {{ic, id, -(ic * tx + id * ty)}},
          {{0.0, 0.0, 1.0}}}};
  return true;
}

}  // namespace dic
