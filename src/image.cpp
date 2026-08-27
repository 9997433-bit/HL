#include "dic/image.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <sstream>

namespace dic {

bool writePGM(const std::string& path, const Image& img, double vmin, double vmax) {
  std::ofstream os(path, std::ios::binary);
  if (!os) return false;
  os << "P5\n" << img.width << " " << img.height << "\n255\n";
  const double scale = (vmax > vmin) ? 255.0 / (vmax - vmin) : 0.0;
  std::string buf;
  buf.reserve(static_cast<size_t>(img.width) * img.height);
  for (double v : img.data) {
    double s = (v - vmin) * scale;
    s = std::clamp(s, 0.0, 255.0);
    buf.push_back(static_cast<char>(static_cast<unsigned char>(std::lround(s))));
  }
  os.write(buf.data(), static_cast<std::streamsize>(buf.size()));
  return static_cast<bool>(os);
}

bool readPGM(const std::string& path, Image& img) {
  std::ifstream is(path, std::ios::binary);
  if (!is) return false;
  std::string magic;
  is >> magic;
  if (magic != "P5") return false;
  int w = 0, h = 0, maxv = 0;
  is >> w >> h >> maxv;
  is.get();  // consume single whitespace after header
  if (w <= 0 || h <= 0 || maxv <= 0) return false;
  img = Image(w, h);
  std::string buf(static_cast<size_t>(w) * h, '\0');
  is.read(buf.data(), static_cast<std::streamsize>(buf.size()));
  for (size_t i = 0; i < buf.size(); ++i)
    img.data[i] = static_cast<unsigned char>(buf[i]);
  return true;
}

}  // namespace dic
