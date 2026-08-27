#pragma once

#include <array>
#include <cmath>

namespace dic {

// Solve a 6x6 linear system A x = b via Gaussian elimination with partial
// pivoting. Returns false when the system is (numerically) singular.
inline bool solve6(std::array<std::array<double, 6>, 6> A,
                   std::array<double, 6> b,
                   std::array<double, 6>& x) {
  constexpr int n = 6;
  for (int k = 0; k < n; ++k) {
    int piv = k;
    double best = std::fabs(A[k][k]);
    for (int i = k + 1; i < n; ++i) {
      const double v = std::fabs(A[i][k]);
      if (v > best) {
        best = v;
        piv = i;
      }
    }
    if (best < 1e-14) return false;
    if (piv != k) {
      std::swap(A[piv], A[k]);
      std::swap(b[piv], b[k]);
    }
    for (int i = k + 1; i < n; ++i) {
      const double f = A[i][k] / A[k][k];
      for (int j = k; j < n; ++j) A[i][j] -= f * A[k][j];
      b[i] -= f * b[k];
    }
  }
  for (int i = n - 1; i >= 0; --i) {
    double s = b[i];
    for (int j = i + 1; j < n; ++j) s -= A[i][j] * x[j];
    x[i] = s / A[i][i];
  }
  return true;
}

}  // namespace dic
