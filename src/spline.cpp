#include "dic/spline.hpp"

#include <cmath>
#include <vector>

namespace dic {

namespace {

// Cubic B-spline pole (Unser). lambda = (1 - z)(1 - 1/z) = 6 for this pole.
constexpr double kPole = -0.2679491924311227064725537;  // sqrt(3) - 2
constexpr double kLambda = 6.0;

double initialCausal(const std::vector<double>& c, int n, double z) {
  // Truncated mirror-boundary initialization (tolerance 1e-9).
  const int horizon = std::min(n, 18);
  double zn = z, sum = c[0];
  for (int k = 1; k < horizon; ++k) {
    sum += zn * c[k];
    zn *= z;
  }
  return sum;
}

double initialAntiCausal(const std::vector<double>& c, int n, double z) {
  return (z / (z * z - 1.0)) * (z * c[n - 2] + c[n - 1]);
}

// In-place prefilter of a single line (length n, stride s) into B-spline coeffs.
void prefilterLine(std::vector<double>& data, int start, int stride, int n) {
  std::vector<double> c(n);
  for (int i = 0; i < n; ++i) c[i] = data[start + i * stride] * kLambda;
  c[0] = initialCausal(c, n, kPole);
  for (int i = 1; i < n; ++i) c[i] += kPole * c[i - 1];
  c[n - 1] = initialAntiCausal(c, n, kPole);
  for (int i = n - 2; i >= 0; --i) c[i] = kPole * (c[i + 1] - c[i]);
  for (int i = 0; i < n; ++i) data[start + i * stride] = c[i];
}

int mirror(int i, int n) {
  if (n == 1) return 0;
  const int period = 2 * (n - 1);
  i = std::abs(i) % period;
  if (i >= n) i = period - i;
  return i;
}

// Cubic B-spline value weights for fractional t in [0, 1), taps at i-1..i+2.
inline void cubicWeights(double t, double w[4]) {
  const double t1 = 1.0 - t;
  w[0] = t1 * t1 * t1 / 6.0;
  w[1] = 2.0 / 3.0 - t * t + 0.5 * t * t * t;
  w[2] = 2.0 / 3.0 - t1 * t1 + 0.5 * t1 * t1 * t1;
  w[3] = t * t * t / 6.0;
}

// Derivatives of the cubic B-spline weights w.r.t. the coordinate.
inline void cubicWeightsDeriv(double t, double dw[4]) {
  const double t1 = 1.0 - t;
  dw[0] = -0.5 * t1 * t1;
  dw[1] = -2.0 * t + 1.5 * t * t;
  dw[2] = 2.0 * t1 - 1.5 * t1 * t1;
  dw[3] = 0.5 * t * t;
}

}  // namespace

void BSplineImage::build(const Image& img) {
  width_ = img.width;
  height_ = img.height;
  c_ = img.data;
  for (int y = 0; y < height_; ++y) prefilterLine(c_, y * width_, 1, width_);
  for (int x = 0; x < width_; ++x) prefilterLine(c_, x, width_, height_);
}

double BSplineImage::coeff(int x, int y) const {
  return c_[static_cast<size_t>(mirror(y, height_)) * width_ + mirror(x, width_)];
}

double BSplineImage::eval(double x, double y) const {
  const int ix = static_cast<int>(std::floor(x));
  const int iy = static_cast<int>(std::floor(y));
  double wx[4], wy[4];
  cubicWeights(x - ix, wx);
  cubicWeights(y - iy, wy);
  double value = 0.0;
  for (int n = 0; n < 4; ++n) {
    double row = 0.0;
    for (int m = 0; m < 4; ++m) row += coeff(ix - 1 + m, iy - 1 + n) * wx[m];
    value += row * wy[n];
  }
  return value;
}

void BSplineImage::evalGrad(double x, double y, double& value, double& gx,
                            double& gy) const {
  const int ix = static_cast<int>(std::floor(x));
  const int iy = static_cast<int>(std::floor(y));
  double wx[4], wy[4], dwx[4], dwy[4];
  cubicWeights(x - ix, wx);
  cubicWeights(y - iy, wy);
  cubicWeightsDeriv(x - ix, dwx);
  cubicWeightsDeriv(y - iy, dwy);
  value = 0.0;
  gx = 0.0;
  gy = 0.0;
  for (int n = 0; n < 4; ++n) {
    double row = 0.0, drow = 0.0;
    for (int m = 0; m < 4; ++m) {
      const double cc = coeff(ix - 1 + m, iy - 1 + n);
      row += cc * wx[m];
      drow += cc * dwx[m];
    }
    value += row * wy[n];
    gx += drow * wy[n];
    gy += row * dwy[n];
  }
}

}  // namespace dic
