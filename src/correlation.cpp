#include "dic/correlation.hpp"

#include <algorithm>
#include <cmath>
#include <queue>
#include <vector>

#include "dic/interpolation.hpp"

namespace dic {

namespace {

// Integer-pixel initial guess by maximizing ZNCC over a translation search.
void integerGuess(const Image& ref, const Image& def, int x0, int y0, int R,
                  int S, int& bestDu, int& bestDv, double& bestZncc) {
  bestZncc = -2.0;
  bestDu = 0;
  bestDv = 0;

  double fMean = 0.0;
  int count = 0;
  for (int j = -R; j <= R; ++j)
    for (int i = -R; i <= R; ++i) {
      fMean += ref.at(x0 + i, y0 + j);
      ++count;
    }
  fMean /= count;
  double fNorm2 = 0.0;
  for (int j = -R; j <= R; ++j)
    for (int i = -R; i <= R; ++i) {
      const double d = ref.at(x0 + i, y0 + j) - fMean;
      fNorm2 += d * d;
    }
  const double fNorm = std::sqrt(fNorm2);
  if (fNorm < 1e-9) return;

  for (int dv = -S; dv <= S; ++dv) {
    for (int du = -S; du <= S; ++du) {
      const int cx = x0 + du, cy = y0 + dv;
      if (!def.inBounds(cx - R, cy - R) || !def.inBounds(cx + R, cy + R)) continue;
      double gMean = 0.0;
      for (int j = -R; j <= R; ++j)
        for (int i = -R; i <= R; ++i) gMean += def.at(cx + i, cy + j);
      gMean /= count;
      double gNorm2 = 0.0, cross = 0.0;
      for (int j = -R; j <= R; ++j)
        for (int i = -R; i <= R; ++i) {
          const double dg = def.at(cx + i, cy + j) - gMean;
          gNorm2 += dg * dg;
          cross += (ref.at(x0 + i, y0 + j) - fMean) * dg;
        }
      const double gNorm = std::sqrt(gNorm2);
      if (gNorm < 1e-9) continue;
      const double zncc = cross / (fNorm * gNorm);
      if (zncc > bestZncc) {
        bestZncc = zncc;
        bestDu = du;
        bestDv = dv;
      }
    }
  }
}

struct QueueItem {
  double zncc;
  int index;
  bool operator<(const QueueItem& o) const { return zncc < o.zncc; }  // max-heap
};

}  // namespace

DICField correlate(const Image& ref, const Image& def, const ROI& roi,
                   const DICOptions& opt) {
  const int R = opt.icgn.subsetRadius;
  const int margin = R + opt.searchRadius + 2;

  const int xlo = std::max(roi.x0, margin);
  const int ylo = std::max(roi.y0, margin);
  const int xhi = std::min(roi.x1, ref.width - 1 - margin);
  const int yhi = std::min(roi.y1, ref.height - 1 - margin);

  DICField field;
  field.step = opt.step;
  if (xhi < xlo || yhi < ylo) return field;

  field.cols = (xhi - xlo) / opt.step + 1;
  field.rows = (yhi - ylo) / opt.step + 1;
  field.points.resize(static_cast<size_t>(field.cols) * field.rows);
  for (int r = 0; r < field.rows; ++r)
    for (int c = 0; c < field.cols; ++c) {
      POI& poi = field.at(c, r);
      poi.x = xlo + c * opt.step;
      poi.y = ylo + r * opt.step;
    }

  // Path-independent mode: each point is solved from its own integer-pixel
  // guess, so the grid is embarrassingly parallel.
  if (opt.pathIndependent) {
    const int nPts = static_cast<int>(field.points.size());
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 16)
#endif
    for (int i = 0; i < nPts; ++i) {
      POI& poi = field.points[i];
      int du, dv;
      double z;
      integerGuess(ref, def, poi.x, poi.y, R, opt.searchRadius, du, dv, z);
      Params init;
      init.u = du;
      init.v = dv;
      const ICGNResult res = icgnMatch(ref, def, poi.x, poi.y, init, opt.icgn);
      poi.params = res.params;
      poi.zncc = res.zncc;
      poi.iterations = res.iterations;
      poi.valid = res.converged && res.zncc >= opt.znccThreshold;
    }
    return field;
  }

  std::vector<char> visited(field.points.size(), 0);
  std::priority_queue<QueueItem> pq;

  // Seed at the grid point nearest the ROI center.
  const int seedC = field.cols / 2;
  const int seedR = field.rows / 2;
  const int seedIdx = seedR * field.cols + seedC;
  {
    POI& seed = field.at(seedC, seedR);
    int du, dv;
    double z;
    integerGuess(ref, def, seed.x, seed.y, R, opt.searchRadius, du, dv, z);
    Params init;
    init.u = du;
    init.v = dv;
    const ICGNResult res = icgnMatch(ref, def, seed.x, seed.y, init, opt.icgn);
    seed.params = res.params;
    seed.zncc = res.zncc;
    seed.iterations = res.iterations;
    seed.valid = res.converged && res.zncc >= opt.znccThreshold;
    visited[seedIdx] = 1;
    if (seed.valid) pq.push({seed.zncc, seedIdx});
  }

  const int dCol[4] = {1, -1, 0, 0};
  const int dRow[4] = {0, 0, 1, -1};
  while (!pq.empty()) {
    const QueueItem top = pq.top();
    pq.pop();
    const int c = top.index % field.cols;
    const int r = top.index / field.cols;
    const Params seedParams = field.at(c, r).params;

    for (int k = 0; k < 4; ++k) {
      const int nc = c + dCol[k];
      const int nr = r + dRow[k];
      if (nc < 0 || nr < 0 || nc >= field.cols || nr >= field.rows) continue;
      const int nIdx = nr * field.cols + nc;
      if (visited[nIdx]) continue;
      visited[nIdx] = 1;

      POI& poi = field.at(nc, nr);
      const ICGNResult res = icgnMatch(ref, def, poi.x, poi.y, seedParams, opt.icgn);
      poi.params = res.params;
      poi.zncc = res.zncc;
      poi.iterations = res.iterations;
      poi.valid = res.converged && res.zncc >= opt.znccThreshold;
      if (poi.valid) pq.push({poi.zncc, nIdx});
    }
  }

  return field;
}

}  // namespace dic
