#pragma once

#include <vector>

#include "dic/image.hpp"

namespace dic {

// Prefiltered cubic B-spline image model. Interpolation coefficients are
// computed once via the Unser/Thevenaz recursive causal/anti-causal filter
// (mirror boundary). Sampling uses the tensor-product cubic B-spline basis;
// gradients are the analytic derivative of that same basis (so the gradient is
// consistent with the interpolant, which matters for the IC-GN fixed point).
class BSplineImage {
 public:
  BSplineImage() = default;
  explicit BSplineImage(const Image& img) { build(img); }

  void build(const Image& img);

  int width() const { return width_; }
  int height() const { return height_; }

  double eval(double x, double y) const;
  void evalGrad(double x, double y, double& value, double& gx, double& gy) const;

 private:
  double coeff(int x, int y) const;  // mirror-boundary coefficient access

  int width_ = 0, height_ = 0;
  std::vector<double> c_;  // B-spline coefficients, row-major
};

}  // namespace dic
