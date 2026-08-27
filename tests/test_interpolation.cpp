#include <cmath>

#include "dic/image.hpp"
#include "dic/interpolation.hpp"
#include "test_util.hpp"

using namespace dic;

int main() {
  // Bicubic (Keys) reproduces a linear intensity field exactly.
  Image img(32, 32);
  auto linear = [](double x, double y) { return 2.0 * x + 3.0 * y + 5.0; };
  for (int y = 0; y < img.height; ++y)
    for (int x = 0; x < img.width; ++x) img.at(x, y) = linear(x, y);

  CHECK_NEAR(bicubic(img, 10.0, 20.0), linear(10.0, 20.0), 1e-9);
  CHECK_NEAR(bicubic(img, 10.3, 20.7), linear(10.3, 20.7), 1e-6);
  CHECK_NEAR(bicubic(img, 5.5, 5.5), linear(5.5, 5.5), 1e-6);

  // Gradients of the linear field are exactly the slopes.
  CHECK_NEAR(gradX(img, 16, 16), 2.0, 1e-9);
  CHECK_NEAR(gradY(img, 16, 16), 3.0, 1e-9);

  // Analytic bicubic gradient reproduces value and exact slopes of the linear field.
  double val, gx, gy;
  bicubicWithGrad(img, 12.4, 18.6, val, gx, gy);
  CHECK_NEAR(val, linear(12.4, 18.6), 1e-6);
  CHECK_NEAR(gx, 2.0, 1e-6);
  CHECK_NEAR(gy, 3.0, 1e-6);

  // Analytic gradient agrees with a central finite difference on a smooth field.
  Image q(40, 40);
  for (int y = 0; y < q.height; ++y)
    for (int x = 0; x < q.width; ++x)
      q.at(x, y) = std::sin(0.2 * x) * std::cos(0.15 * y) * 50.0 + 128.0;
  double v0, qgx, qgy;
  bicubicWithGrad(q, 20.3, 15.7, v0, qgx, qgy);
  const double h = 1e-3;
  const double fdX = (bicubic(q, 20.3 + h, 15.7) - bicubic(q, 20.3 - h, 15.7)) / (2 * h);
  const double fdY = (bicubic(q, 20.3, 15.7 + h) - bicubic(q, 20.3, 15.7 - h)) / (2 * h);
  CHECK_NEAR(qgx, fdX, 1e-3);
  CHECK_NEAR(qgy, fdY, 1e-3);

  TEST_REPORT();
}
