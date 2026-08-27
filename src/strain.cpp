#include "dic/strain.hpp"

#include <array>
#include <cmath>

namespace dic {

namespace {

// Solve a symmetric 3x3 system M a = r via Cramer's rule. Returns false if
// (numerically) singular.
bool solve3(const std::array<std::array<double, 3>, 3>& M,
            const std::array<double, 3>& r, std::array<double, 3>& a) {
  const double det =
      M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) -
      M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) +
      M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
  if (std::fabs(det) < 1e-12) return false;
  const double inv = 1.0 / det;
  for (int col = 0; col < 3; ++col) {
    std::array<std::array<double, 3>, 3> Mc = M;
    for (int row = 0; row < 3; ++row) Mc[row][col] = r[row];
    const double d =
        Mc[0][0] * (Mc[1][1] * Mc[2][2] - Mc[1][2] * Mc[2][1]) -
        Mc[0][1] * (Mc[1][0] * Mc[2][2] - Mc[1][2] * Mc[2][0]) +
        Mc[0][2] * (Mc[1][0] * Mc[2][1] - Mc[1][1] * Mc[2][0]);
    a[col] = d * inv;
  }
  return true;
}

}  // namespace

StrainField computeStrain(const DICField& field, int windowRadius) {
  StrainField sf;
  sf.cols = field.cols;
  sf.rows = field.rows;
  sf.points.resize(field.points.size());

  for (int r = 0; r < field.rows; ++r) {
    for (int c = 0; c < field.cols; ++c) {
      StrainPoint& out = sf.at(c, r);
      const POI& center = field.at(c, r);
      if (!center.valid) continue;

      // Accumulate the least-squares system for a local plane fit of u and v:
      //   z(px, py) = a0 + a1*px + a2*py,  px = X - X0, py = Y - Y0 (pixels).
      std::array<std::array<double, 3>, 3> M{};
      std::array<double, 3> ru{}, rv{};
      int n = 0;
      for (int dr = -windowRadius; dr <= windowRadius; ++dr) {
        for (int dc = -windowRadius; dc <= windowRadius; ++dc) {
          const int nc = c + dc, nr = r + dr;
          if (nc < 0 || nr < 0 || nc >= field.cols || nr >= field.rows) continue;
          const POI& p = field.at(nc, nr);
          if (!p.valid) continue;
          const double px = static_cast<double>(p.x - center.x);
          const double py = static_cast<double>(p.y - center.y);
          M[0][0] += 1;      M[0][1] += px;      M[0][2] += py;
          M[1][0] += px;     M[1][1] += px * px; M[1][2] += px * py;
          M[2][0] += py;     M[2][1] += px * py; M[2][2] += py * py;
          ru[0] += p.params.u;  ru[1] += px * p.params.u;  ru[2] += py * p.params.u;
          rv[0] += p.params.v;  rv[1] += px * p.params.v;  rv[2] += py * p.params.v;
          ++n;
        }
      }
      if (n < 3) continue;

      std::array<double, 3> au{}, av{};
      if (!solve3(M, ru, au) || !solve3(M, rv, av)) continue;

      const double dudx = au[1], dudy = au[2];
      const double dvdx = av[1], dvdy = av[2];
      out.dudx = dudx;
      out.dudy = dudy;
      out.dvdx = dvdx;
      out.dvdy = dvdy;
      // Green-Lagrange: E = 1/2 (F^T F - I), F = I + grad(u).
      out.Exx = dudx + 0.5 * (dudx * dudx + dvdx * dvdx);
      out.Eyy = dvdy + 0.5 * (dudy * dudy + dvdy * dvdy);
      out.Exy = 0.5 * (dudy + dvdx) + 0.5 * (dudx * dudy + dvdx * dvdy);
      out.valid = true;
    }
  }
  return sf;
}

}  // namespace dic
