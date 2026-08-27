#pragma once

#include "dic/image.hpp"

namespace dic {

// Bicubic (Keys, a = -0.5) intensity interpolation at real-valued coordinates.
// Out-of-range samples are clamped to the image border.
double bicubic(const Image& img, double x, double y);

// Reference-image gradients via central differences at integer coordinates.
double gradX(const Image& img, int x, int y);
double gradY(const Image& img, int x, int y);

}  // namespace dic
