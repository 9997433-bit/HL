#pragma once

#include "dic/image.hpp"

namespace dic {

// Bicubic (Keys, a = -0.5) intensity interpolation at real-valued coordinates.
// Out-of-range samples are clamped to the image border.
double bicubic(const Image& img, double x, double y);

// Bicubic interpolation returning the value and the analytic spatial gradient
// (partial derivatives of the interpolant w.r.t. x and y).
void bicubicWithGrad(const Image& img, double x, double y, double& value,
                     double& gx, double& gy);

// Reference-image gradients via central differences at integer coordinates.
double gradX(const Image& img, int x, int y);
double gradY(const Image& img, int x, int y);

}  // namespace dic
