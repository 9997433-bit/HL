#include "dic/icgn.hpp"

#include <array>
#include <cmath>
#include <vector>

#include "dic/interpolation.hpp"
#include "dic/linalg.hpp"

namespace dic {

namespace {

struct SubsetPixel {
  double dx, dy;             // local subset coordinates
  double f;                  // reference intensity
  std::array<double, 6> sdi; // steepest-descent image (grad f * dW/dp)
};

}  // namespace

ICGNResult icgnMatch(const Image& ref, const Image& def, int x0, int y0,
                     const Params& init, const ICGNOptions& opt) {
  const int R = opt.subsetRadius;
  ICGNResult result;
  result.params = init;

  // --- Precompute reference subset, gradients, steepest-descent images and the
  //     (constant) Hessian. This is the inverse-compositional advantage. ---
  std::vector<SubsetPixel> subset;
  subset.reserve(static_cast<size_t>(2 * R + 1) * (2 * R + 1));
  double fMean = 0.0;
  for (int j = -R; j <= R; ++j) {
    for (int i = -R; i <= R; ++i) {
      const int x = x0 + i;
      const int y = y0 + j;
      if (!ref.inBounds(x, y)) return result;  // subset leaves the image
      const double f = ref.at(x, y);
      const double gx = gradX(ref, x, y);
      const double gy = gradY(ref, x, y);
      const double dx = i, dy = j;
      SubsetPixel px;
      px.dx = dx;
      px.dy = dy;
      px.f = f;
      px.sdi = {gx, gx * dx, gx * dy, gy, gy * dx, gy * dy};
      subset.push_back(px);
      fMean += f;
    }
  }
  const double n = static_cast<double>(subset.size());
  fMean /= n;

  double fNorm2 = 0.0;
  for (const auto& px : subset) {
    const double d = px.f - fMean;
    fNorm2 += d * d;
  }
  const double fNorm = std::sqrt(fNorm2);
  if (fNorm < 1e-9) return result;  // reference subset has no contrast

  std::array<std::array<double, 6>, 6> H{};
  for (const auto& px : subset)
    for (int a = 0; a < 6; ++a)
      for (int b = 0; b < 6; ++b) H[a][b] += px.sdi[a] * px.sdi[b];

  // --- Iterate ---
  std::vector<double> g(subset.size());
  for (int iter = 0; iter < opt.maxIterations; ++iter) {
    const Params& p = result.params;

    double gMean = 0.0;
    bool outside = false;
    for (size_t k = 0; k < subset.size(); ++k) {
      const double dx = subset[k].dx, dy = subset[k].dy;
      const double wx = x0 + dx + p.u + p.ux * dx + p.uy * dy;
      const double wy = y0 + dy + p.v + p.vx * dx + p.vy * dy;
      if (wx < 0 || wy < 0 || wx > def.width - 1 || wy > def.height - 1) {
        outside = true;
        break;
      }
      g[k] = bicubic(def, wx, wy);
      gMean += g[k];
    }
    if (outside) {
      result.iterations = iter;
      return result;
    }
    gMean /= n;

    double gNorm2 = 0.0;
    for (double gv : g) {
      const double d = gv - gMean;
      gNorm2 += d * d;
    }
    const double gNorm = std::sqrt(gNorm2);
    if (gNorm < 1e-9) {
      result.iterations = iter;
      return result;
    }

    const double ratio = fNorm / gNorm;
    std::array<double, 6> b{};
    for (size_t k = 0; k < subset.size(); ++k) {
      const double e = ratio * (g[k] - gMean) - (subset[k].f - fMean);
      for (int a = 0; a < 6; ++a) b[a] += subset[k].sdi[a] * e;
    }

    std::array<double, 6> dp{};
    if (!solve6(H, b, dp)) {
      result.iterations = iter;
      return result;
    }

    // Inverse-compositional update: W(p) <- W(p) . W(dp)^{-1}
    Params dpar;
    dpar.u = dp[0];
    dpar.ux = dp[1];
    dpar.uy = dp[2];
    dpar.v = dp[3];
    dpar.vx = dp[4];
    dpar.vy = dp[5];
    Mat3 invDp;
    if (!invertAffine(warpMatrix(dpar), invDp)) {
      result.iterations = iter;
      return result;
    }
    const Mat3 updated = matMul(warpMatrix(p), invDp);
    result.params = paramsFromMatrix(updated);
    result.iterations = iter + 1;

    // Convergence: magnitude of incremental warp at the subset corner.
    const double zeta = std::sqrt(
        dp[0] * dp[0] + dp[3] * dp[3] +
        (dp[1] * dp[1] + dp[2] * dp[2] + dp[4] * dp[4] + dp[5] * dp[5]) *
            static_cast<double>(R) * static_cast<double>(R));
    if (zeta < opt.convergenceTol) {
      result.converged = true;
      break;
    }
  }

  // --- Final ZNCC at the converged warp ---
  const Params& p = result.params;
  double gMean = 0.0;
  bool outside = false;
  for (size_t k = 0; k < subset.size(); ++k) {
    const double dx = subset[k].dx, dy = subset[k].dy;
    const double wx = x0 + dx + p.u + p.ux * dx + p.uy * dy;
    const double wy = y0 + dy + p.v + p.vx * dx + p.vy * dy;
    if (wx < 0 || wy < 0 || wx > def.width - 1 || wy > def.height - 1) {
      outside = true;
      break;
    }
    g[k] = bicubic(def, wx, wy);
    gMean += g[k];
  }
  if (!outside) {
    gMean /= n;
    double gNorm2 = 0.0, cross = 0.0;
    for (size_t k = 0; k < subset.size(); ++k) {
      const double dg = g[k] - gMean;
      gNorm2 += dg * dg;
      cross += (subset[k].f - fMean) * dg;
    }
    const double gNorm = std::sqrt(gNorm2);
    if (gNorm > 1e-9) result.zncc = cross / (fNorm * gNorm);
  }
  return result;
}

ICGNResult icgnMatchSpline(const BSplineImage& ref, const BSplineImage& def,
                           int x0, int y0, const Params& init,
                           const ICGNOptions& opt) {
  const int R = opt.subsetRadius;
  ICGNResult result;
  result.params = init;

  std::vector<SubsetPixel> subset;
  subset.reserve(static_cast<size_t>(2 * R + 1) * (2 * R + 1));
  double fMean = 0.0;
  for (int j = -R; j <= R; ++j) {
    for (int i = -R; i <= R; ++i) {
      const int x = x0 + i, y = y0 + j;
      if (x < 0 || y < 0 || x >= ref.width() || y >= ref.height()) return result;
      double f, gx, gy;
      ref.evalGrad(x, y, f, gx, gy);  // spline-consistent reference gradients
      const double dx = i, dy = j;
      SubsetPixel px;
      px.dx = dx;
      px.dy = dy;
      px.f = f;
      px.sdi = {gx, gx * dx, gx * dy, gy, gy * dx, gy * dy};
      subset.push_back(px);
      fMean += f;
    }
  }
  const double n = static_cast<double>(subset.size());
  fMean /= n;
  double fNorm2 = 0.0;
  for (const auto& px : subset) fNorm2 += (px.f - fMean) * (px.f - fMean);
  const double fNorm = std::sqrt(fNorm2);
  if (fNorm < 1e-9) return result;

  std::array<std::array<double, 6>, 6> H{};
  for (const auto& px : subset)
    for (int a = 0; a < 6; ++a)
      for (int b = 0; b < 6; ++b) H[a][b] += px.sdi[a] * px.sdi[b];

  std::vector<double> g(subset.size());
  for (int iter = 0; iter < opt.maxIterations; ++iter) {
    const Params& p = result.params;
    double gMean = 0.0;
    bool outside = false;
    for (size_t k = 0; k < subset.size(); ++k) {
      const double dx = subset[k].dx, dy = subset[k].dy;
      const double wx = x0 + dx + p.u + p.ux * dx + p.uy * dy;
      const double wy = y0 + dy + p.v + p.vx * dx + p.vy * dy;
      if (wx < 0 || wy < 0 || wx > def.width() - 1 || wy > def.height() - 1) {
        outside = true;
        break;
      }
      g[k] = def.eval(wx, wy);
      gMean += g[k];
    }
    if (outside) {
      result.iterations = iter;
      return result;
    }
    gMean /= n;
    double gNorm2 = 0.0;
    for (double gv : g) gNorm2 += (gv - gMean) * (gv - gMean);
    const double gNorm = std::sqrt(gNorm2);
    if (gNorm < 1e-9) {
      result.iterations = iter;
      return result;
    }
    const double ratio = fNorm / gNorm;
    std::array<double, 6> b{};
    for (size_t k = 0; k < subset.size(); ++k) {
      const double e = ratio * (g[k] - gMean) - (subset[k].f - fMean);
      for (int a = 0; a < 6; ++a) b[a] += subset[k].sdi[a] * e;
    }
    std::array<double, 6> dp{};
    if (!solve6(H, b, dp)) {
      result.iterations = iter;
      return result;
    }
    Params dpar;
    dpar.u = dp[0];
    dpar.ux = dp[1];
    dpar.uy = dp[2];
    dpar.v = dp[3];
    dpar.vx = dp[4];
    dpar.vy = dp[5];
    Mat3 invDp;
    if (!invertAffine(warpMatrix(dpar), invDp)) {
      result.iterations = iter;
      return result;
    }
    result.params = paramsFromMatrix(matMul(warpMatrix(p), invDp));
    result.iterations = iter + 1;
    const double zeta = std::sqrt(
        dp[0] * dp[0] + dp[3] * dp[3] +
        (dp[1] * dp[1] + dp[2] * dp[2] + dp[4] * dp[4] + dp[5] * dp[5]) *
            static_cast<double>(R) * static_cast<double>(R));
    if (zeta < opt.convergenceTol) {
      result.converged = true;
      break;
    }
  }

  const Params& p = result.params;
  double gMean = 0.0;
  bool outside = false;
  for (size_t k = 0; k < subset.size(); ++k) {
    const double dx = subset[k].dx, dy = subset[k].dy;
    const double wx = x0 + dx + p.u + p.ux * dx + p.uy * dy;
    const double wy = y0 + dy + p.v + p.vx * dx + p.vy * dy;
    if (wx < 0 || wy < 0 || wx > def.width() - 1 || wy > def.height() - 1) {
      outside = true;
      break;
    }
    g[k] = def.eval(wx, wy);
    gMean += g[k];
  }
  if (!outside) {
    gMean /= n;
    double gNorm2 = 0.0, cross = 0.0;
    for (size_t k = 0; k < subset.size(); ++k) {
      const double dg = g[k] - gMean;
      gNorm2 += dg * dg;
      cross += (subset[k].f - fMean) * dg;
    }
    const double gNorm = std::sqrt(gNorm2);
    if (gNorm > 1e-9) result.zncc = cross / (fNorm * gNorm);
  }
  return result;
}

}  // namespace dic
