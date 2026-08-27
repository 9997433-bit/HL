#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace dic {

// Dense single-channel image with double precision intensities. Row-major.
struct Image {
  int width = 0;
  int height = 0;
  std::vector<double> data;

  Image() = default;
  Image(int w, int h) : width(w), height(h), data(static_cast<size_t>(w) * h, 0.0) {}

  double& at(int x, int y) { return data[static_cast<size_t>(y) * width + x]; }
  double at(int x, int y) const { return data[static_cast<size_t>(y) * width + x]; }

  bool inBounds(int x, int y) const {
    return x >= 0 && y >= 0 && x < width && y < height;
  }
};

// Dependency-free PGM I/O (binary P5), used for tests and visualization.
bool writePGM(const std::string& path, const Image& img, double vmin, double vmax);
bool readPGM(const std::string& path, Image& img);

}  // namespace dic
