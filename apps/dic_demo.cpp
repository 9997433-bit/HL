#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "dic/correlation.hpp"
#include "dic/image.hpp"
#include "dic/strain.hpp"
#include "dic/synthetic.hpp"

using namespace dic;

namespace {

// Write a color heatmap (PPM/P6) of a scalar field using a simple
// blue-white-red colormap over [vmin, vmax].
void writeHeatmapPPM(const std::string& path, const std::vector<double>& v,
                     const std::vector<char>& valid, int cols, int rows,
                     double vmin, double vmax, int cell) {
  const int W = cols * cell, H = rows * cell;
  std::vector<unsigned char> rgb(static_cast<size_t>(W) * H * 3, 32);
  const double span = (vmax > vmin) ? (vmax - vmin) : 1.0;
  for (int r = 0; r < rows; ++r)
    for (int c = 0; c < cols; ++c) {
      const size_t k = static_cast<size_t>(r) * cols + c;
      unsigned char R = 40, G = 40, B = 48;
      if (valid[k]) {
        double t = (v[k] - vmin) / span;
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        // blue (0) -> white (0.5) -> red (1)
        if (t < 0.5) {
          const double s = t / 0.5;
          R = static_cast<unsigned char>(255 * s);
          G = static_cast<unsigned char>(255 * s);
          B = 255;
        } else {
          const double s = (t - 0.5) / 0.5;
          R = 255;
          G = static_cast<unsigned char>(255 * (1 - s));
          B = static_cast<unsigned char>(255 * (1 - s));
        }
      }
      for (int dy = 0; dy < cell; ++dy)
        for (int dx = 0; dx < cell; ++dx) {
          const int x = c * cell + dx, y = r * cell + dy;
          const size_t o = (static_cast<size_t>(y) * W + x) * 3;
          rgb[o] = R;
          rgb[o + 1] = G;
          rgb[o + 2] = B;
        }
    }
  FILE* fp = std::fopen(path.c_str(), "wb");
  if (!fp) return;
  std::fprintf(fp, "P6\n%d %d\n255\n", W, H);
  std::fwrite(rgb.data(), 1, rgb.size(), fp);
  std::fclose(fp);
}

}  // namespace

int main(int argc, char** argv) {
  std::string outDir = (argc > 1) ? argv[1] : ".";

  const int W = 512, H = 512;
  // Inverse-crime-free: build an analytic (non-saturating) speckle pattern and
  // render both images from it directly (no shared interpolant).
  const SpecklePattern pattern = makeSpecklePattern(W, H, 9000, 2.0, 7u, 25.0, 60.0);
  Image ref = renderPattern(pattern, W, H, 0.0, 0.0);

  // Prescribed affine deformation: translation + strain about the image center.
  AffineField field;
  field.center = {W / 2.0, H / 2.0};
  field.t = {0.75, -0.40};
  field.A = {{{{0.010, 0.002}}, {{0.001, -0.006}}}};
  Image def = renderAffine(pattern, W, H, field);

  DICOptions opt;
  opt.icgn.subsetRadius = 20;
  opt.icgn.maxIterations = 50;
  opt.icgn.convergenceTol = 1e-4;
  opt.step = 8;
  opt.searchRadius = 6;
  opt.znccThreshold = 0.9;
  opt.pathIndependent = true;  // OpenMP-parallel, path-independent

  ROI roi{0, 0, W - 1, H - 1};

  // Honest Keys-vs-B-spline comparison of full-field displacement RMS error.
  auto rmsOf = [&](bool bspline) {
    DICOptions o = opt;
    o.useBSpline = bspline;
    DICField ff = correlate(ref, def, roi, o);
    int v = 0;
    double s = 0.0;
    for (const POI& p : ff.points) {
      if (!p.valid) continue;
      ++v;
      double ug, vg;
      field.displacement(p.x, p.y, ug, vg);
      s += (p.params.u - ug) * (p.params.u - ug) + (p.params.v - vg) * (p.params.v - vg);
    }
    return std::sqrt(s / std::max(v, 1));
  };
  const double rmsKeys = rmsOf(false);
  const double rmsBspline = rmsOf(true);

  opt.useBSpline = true;
  const auto t0 = std::chrono::steady_clock::now();
  DICField f = correlate(ref, def, roi, opt);
  const auto t1 = std::chrono::steady_clock::now();
  const double corrMs = std::chrono::duration<double, std::milli>(t1 - t0).count();
  StrainField strain = computeStrain(f, 2);

  // Accuracy against the analytic ground-truth field.
  int valid = 0, total = 0, iters = 0;
  double sU = 0, sV = 0, maxErr = 0, sZ = 0;
  double sExx = 0, sEyy = 0, sExy = 0;
  std::vector<double> uField(f.points.size()), vField(f.points.size());
  std::vector<double> exxField(f.points.size());
  std::vector<char> mask(f.points.size(), 0);
  std::vector<char> strainMask(f.points.size(), 0);
  double sExxG = 0.0;
  int nStrain = 0;
  for (size_t i = 0; i < f.points.size(); ++i) {
    const POI& p = f.points[i];
    ++total;
    if (!p.valid) continue;
    ++valid;
    iters += p.iterations;
    double ugt, vgt;
    field.displacement(p.x, p.y, ugt, vgt);
    const double eu = p.params.u - ugt, ev = p.params.v - vgt;
    sU += eu * eu;
    sV += ev * ev;
    maxErr = std::max(maxErr, std::sqrt(eu * eu + ev * ev));
    sZ += p.zncc;
    sExx += p.params.ux;
    sEyy += p.params.vy;
    sExy += 0.5 * (p.params.uy + p.params.vx);
    uField[i] = p.params.u;
    vField[i] = p.params.v;
    mask[i] = 1;
    if (strain.points[i].valid) {
      exxField[i] = strain.points[i].Exx;
      strainMask[i] = 1;
      sExxG += strain.points[i].Exx;
      ++nStrain;
    }
  }

  const double rmsU = std::sqrt(sU / valid), rmsV = std::sqrt(sV / valid);

  std::printf("=== HL-DIC 2D correlation demo ===\n");
  std::printf("image            : %d x %d speckle\n", W, H);
  std::printf("grid points      : %d valid / %d total (%.1f%%)\n", valid, total,
              100.0 * valid / total);
  std::printf("subset radius    : %d px   step: %d px\n", opt.icgn.subsetRadius, opt.step);
  std::printf("correlation time : %.1f ms (path-independent, OpenMP)\n", corrMs);
  std::printf("mean iterations  : %.1f\n", static_cast<double>(iters) / valid);
  std::printf("mean ZNCC        : %.6f\n", sZ / valid);
  std::printf("--- displacement accuracy vs ground truth (honest analytic rendering) ---\n");
  std::printf("RMS error  u     : %.4f px\n", rmsU);
  std::printf("RMS error  v     : %.4f px\n", rmsV);
  std::printf("max  error |d|   : %.4f px\n", maxErr);
  std::printf("--- interpolation comparison (full-field RMS |d| error) ---\n");
  std::printf("Keys bicubic     : %.4f px\n", rmsKeys);
  std::printf("cubic B-spline   : %.4f px\n", rmsBspline);
  const double a00 = field.A[0][0], a10 = field.A[1][0];
  const double gExx = a00 + 0.5 * (a00 * a00 + a10 * a10);
  std::printf("--- mean strain: raw gradient vs PLS Green-Lagrange vs truth ---\n");
  std::printf("exx (raw)        : %+.5f\n", sExx / valid);
  std::printf("Exx (PLS window) : %+.5f   truth(GL): %+.5f\n", sExxG / nStrain, gExx);
  std::printf("eyy (raw)        : %+.5f  (%.5f)\n", sEyy / valid, field.A[1][1]);
  std::printf("exy (raw)        : %+.5f  (%.5f)\n", sExy / valid,
              0.5 * (field.A[0][1] + field.A[1][0]));

  writePGM(outDir + "/reference.pgm", ref, 0, 255);
  writePGM(outDir + "/deformed.pgm", def, 0, 255);
  writeHeatmapPPM(outDir + "/u_field.ppm", uField, mask, f.cols, f.rows, 0.0, 1.5, 6);
  writeHeatmapPPM(outDir + "/v_field.ppm", vField, mask, f.cols, f.rows, -1.5, 1.0, 6);
  writeHeatmapPPM(outDir + "/exx_field.ppm", exxField, strainMask, f.cols, f.rows,
                  0.004, 0.016, 6);
  std::printf("wrote reference.pgm, deformed.pgm, u_field.ppm, v_field.ppm, exx_field.ppm to %s\n",
              outDir.c_str());
  return 0;
}
