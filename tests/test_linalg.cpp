#include <array>

#include "dic/linalg.hpp"
#include "dic/shape_function.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  // Solve a known SPD system A x = b.
  std::array<std::array<double, 6>, 6> A{};
  for (int i = 0; i < 6; ++i) {
    A[i][i] = 2.0 + i;
    if (i + 1 < 6) {
      A[i][i + 1] = 0.5;
      A[i + 1][i] = 0.5;
    }
  }
  std::array<double, 6> xTrue{{1.0, -2.0, 3.0, 0.5, -1.5, 2.5}};
  std::array<double, 6> b{};
  for (int i = 0; i < 6; ++i) {
    double s = 0.0;
    for (int j = 0; j < 6; ++j) s += A[i][j] * xTrue[j];
    b[i] = s;
  }
  std::array<double, 6> x{};
  CHECK(solve6(A, b, x));
  for (int i = 0; i < 6; ++i) CHECK_NEAR(x[i], xTrue[i], 1e-9);

  // Affine inverse composed with itself yields identity.
  Params p;
  p.u = 3.2;
  p.v = -1.7;
  p.ux = 0.02;
  p.uy = -0.01;
  p.vx = 0.005;
  p.vy = 0.03;
  const Mat3 W = warpMatrix(p);
  Mat3 Winv;
  CHECK(invertAffine(W, Winv));
  const Mat3 I = matMul(W, Winv);
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) CHECK_NEAR(I[i][j], (i == j ? 1.0 : 0.0), 1e-12);

  TEST_REPORT();
}
