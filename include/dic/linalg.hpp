#pragma once

#include <array>
#include <cmath>
#include <vector>

namespace dic {

// Solve a dense n x n system A x = b (A row-major, size n*n) via Gaussian
// elimination with partial pivoting. Returns false when (numerically) singular.
inline bool solveDense(int n, std::vector<double> A, std::vector<double> b,
                       std::vector<double>& x) {
  for (int k = 0; k < n; ++k) {
    int piv = k;
    double best = std::fabs(A[k * n + k]);
    for (int i = k + 1; i < n; ++i) {
      const double v = std::fabs(A[i * n + k]);
      if (v > best) {
        best = v;
        piv = i;
      }
    }
    if (best < 1e-15) return false;
    if (piv != k) {
      for (int j = 0; j < n; ++j) std::swap(A[piv * n + j], A[k * n + j]);
      std::swap(b[piv], b[k]);
    }
    for (int i = k + 1; i < n; ++i) {
      const double f = A[i * n + k] / A[k * n + k];
      for (int j = k; j < n; ++j) A[i * n + j] -= f * A[k * n + j];
      b[i] -= f * b[k];
    }
  }
  x.assign(n, 0.0);
  for (int i = n - 1; i >= 0; --i) {
    double s = b[i];
    for (int j = i + 1; j < n; ++j) s -= A[i * n + j] * x[j];
    x[i] = s / A[i * n + i];
  }
  return true;
}

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
