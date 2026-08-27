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

  TEST_REPORT();
}
