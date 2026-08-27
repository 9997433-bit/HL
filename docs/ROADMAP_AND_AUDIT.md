# HL-DIC: SOTA Audit and Technical Roadmap

**Scope.** This document audits the current 2D DIC core (branch `cursor/dic-vic-2d-core-87ff`)
against the state of the art in the DIC/DVC literature and the leading open-source engines
(OpenCorr, DICe/Sandia, Ncorr, muDIC), and lays out a technical roadmap to reach and exceed
VIC-2D, then extend to VIC-3D (stereo DIC) and VIC-Volume (DVC). All measurements below were
produced on this branch (g++ 13.3.0, `-O3`, Release) and are reproducible with the commands
and the appendix harness given at the end.

**Baseline note.** The audit was performed against commit `74c5ffc` (engine core). While it
was underway, commit `7781755` landed on the same branch, adding a pointwise-least-squares
strain module (`include/dic/strain.hpp`, `src/strain.cpp`), an OpenMP path-independent
correlation mode (`DICOptions::pathIndependent`), and three tests (`test_strain`,
`test_bias`, `test_parallel`). All results in §1 were re-verified at `7781755` (7/7 tests
pass); findings C6 and part of C9 are now *partially addressed*, as annotated inline, and
roadmap items A6/A8 (P5/P6) are updated with the remaining scope. Notably, the new
`test_bias` still generates its deformed images through `warpAffine` — the same-interpolant
path this audit flags as an inverse crime — and reads a max bias of **0.0038 px**, whereas
the analytic-rendering harness (§1.3) measures the true peak bias at **0.0166 px**: a direct,
4× quantification of how much that validation style understates systematic error. (Minor:
`7781755` also introduced an unused-variable warning `a01` in `apps/dic_demo.cpp`.)

---

## 1. Verification of the current state

### 1.1 Build and test status

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=g++
cmake --build build -j
ctest --test-dir build --output-on-failure
```

All tests pass (4/4 at audit baseline `74c5ffc`; 7/7 re-verified at `7781755`):

| Test | Result | Key output |
|---|---|---|
| `test_linalg` | PASS | 6×6 solve + affine warp inverse exact to 1e-12 |
| `test_interpolation` | PASS | bicubic reproduces linear field; gradients exact on linear field |
| `test_icgn` | PASS | translation `u=1.3652 v=-0.7216` (truth 1.37/−0.72), ZNCC 0.988; affine `exx=0.00976 eyy=−0.00706` (truth 0.01/−0.008) |
| `test_correlation` | PASS | 729/729 valid, `rmsU=0.0025 px`, `rmsV=0.0026 px`, `maxErr=0.0115 px`, mean ZNCC 0.99447 |
| `test_strain` (new in `7781755`) | PASS | PLS Green-Lagrange strain from displacement field |
| `test_bias` (new in `7781755`) | PASS | max bias 0.0038 px — but via `warpAffine` (inverse crime, see §1.3) |
| `test_parallel` (new in `7781755`) | PASS | RG 489 ms vs path-independent 250 ms (4 cores), identical rms 0.0036 px |

### 1.2 Demo (`./build/dic_demo /tmp/out`)

At audit baseline `74c5ffc` (reliability-guided, single thread):

```
image            : 512 x 512 speckle
grid points      : 3249 valid / 3249 total (100.0%)
subset radius    : 20 px   step: 8 px
mean iterations  : 6.4
mean ZNCC        : 0.994178
RMS error  u     : 0.0021 px
RMS error  v     : 0.0021 px
max  error |d|   : 0.0134 px
exx  : +0.01004  (0.01000)
eyy  : -0.00598  (-0.00600)
exy  : +0.00150  (0.00150)
```

Wall time 1.16 s single-threaded → **≈ 0.36 ms/POI (≈ 2 800 POI/s)** at subset 41×41,
mean 6.4 IC-GN iterations. This is a healthy baseline for an unoptimized scalar
implementation (no coefficient LUT; see §2.3, §4-A8).

Re-run at `7781755` (path-independent OpenMP mode now default in the demo, 4 cores):
identical accuracy (RMS 0.0021/0.0021 px, max 0.0134 px, 3249/3249 valid), correlation time
569 ms, and the new PLS strain output matches the Green-Lagrange truth to 5 decimals
(`Exx = +0.01005` vs truth `+0.01005`).

### 1.3 Independent accuracy measurement (bias sweep, no "inverse crime")

The bundled tests and demo generate the deformed image with `warpAffine`, which samples the
reference through the **same Keys bicubic interpolant** that the matcher uses. In the inverse
problem literature this is an *inverse crime*: the forward model and the estimator share the
same discretization, so their systematic errors largely cancel and the reported error
(≈ 0.002 px RMS) is optimistic.

To measure the true interpolation-induced systematic error, an audit harness (Appendix A)
renders the speckle **analytically** — the deformed image is the exact Gaussian-sum evaluated
at shifted coordinates, with no interpolation in the image-generation path — and sweeps the
sub-pixel phase of a pure translation. Result (subset radius 15, tol 1e-6, noise-free,
25 POIs per shift):

| shift (px) | mean bias (px) | | shift (px) | mean bias (px) |
|---|---|---|---|---|
| 0.00 | +0.0000 | | 0.55 | −0.0041 |
| 0.05 | +0.0074 | | 0.60 | −0.0081 |
| 0.10 | +0.0125 | | 0.65 | −0.0116 |
| 0.15 | +0.0155 | | 0.70 | −0.0143 |
| 0.20 | **+0.0166** | | 0.75 | −0.0161 |
| 0.25 | +0.0162 | | 0.80 | **−0.0165** |
| 0.30 | +0.0145 | | 0.85 | −0.0154 |
| 0.40 | +0.0083 | | 0.90 | −0.0125 |
| 0.50 | +0.0001 | | 1.00 | −0.0000 |

This is the classic S-shaped sub-pixel bias curve of an interpolant with imperfect frequency
response (Schreier, Braasch & Sutton 2000): zero at integer and half-pixel phase, peak
**|bias| ≈ 0.017 px** near phase 0.2/0.8 — roughly **8× larger** than the RMS error the
inverse-crime demo reports. This, not random noise, is the current accuracy limiter, and it
is invisible to the existing test suite.

Noise floor, measured with the same harness (both images corrupted with Gaussian sensor
noise σ = 2 gray levels, shift 0.5 px, 300 samples): mean error 0.00006 px, **std
0.0019 px** — consistent with the Pan/Wang theoretical floor
`std(u) ≈ √2·σ / √SSSIG` for this high-contrast pattern. Random precision is therefore
fine; systematic bias dominates.

---

## 2. Architecture and correctness audit

### 2.1 What is implemented and verified correct

The core math was re-derived and checked line by line:

- **IC-GN update** (`src/icgn.cpp`): the residual `e = (fNorm/gNorm)·(g−ḡ) − (f−f̄)`,
  the normal equations `H·Δp = Σ Jᵀe` with `J = ∇f·∂W/∂p`, and the update
  `W(p) ← W(p) ∘ W(Δp)⁻¹` exactly match Baker & Matthews' inverse-compositional
  algorithm with Pan's ZNSSD normalization (the common `fNorm²` scaling cancels between
  `H` and `b`). Signs and composition order are correct.
- **Hessian constancy**: `H` and the steepest-descent images are precomputed once from the
  reference subset — the genuine IC advantage is realized.
- **Warp algebra** (`include/dic/shape_function.hpp`): `warpMatrix`/`invertAffine`/`matMul`
  are correct; verified to 1e-12 by `test_linalg`.
- **Convergence criterion**: `‖Δp‖` with first-order terms scaled by the subset radius
  (increment of the warp at the subset corner) is Pan's recommended criterion.
- **Reliability-guided propagation** (`src/correlation.cpp`): ZNCC-ordered max-heap flood
  fill matches Pan (2009) RG-DIC. Popped points read their own already-final parameters —
  no stale-state bug.
- **ZNSSD/ZNCC invariance**: both criteria are invariant to affine intensity changes
  (scale + offset), the correct choice for real illumination.
- **Solver**: partial-pivot Gaussian elimination on the 6×6 SPD system is numerically
  adequate at this size.

The engine is a faithful, minimal implementation of the OpenCorr-style pipeline
(integer ZNCC seed → RG propagation → first-order IC-GN with ZNSSD). The foundation is
sound; the gaps below are about accuracy limits, robustness, and missing subsystems.

### 2.2 Correctness risks and accuracy limitations (ranked)

**C1 — Validation is an inverse crime (severity: high, affects all quality claims).**
`warpAffine` (`src/synthetic.cpp`) uses the matcher's own bicubic to synthesize the deformed
image, so tests cannot see interpolation bias (§1.3) and contain no sensor noise. Every
accuracy number currently in the test suite overstates real-world accuracy. The `test_bias`
added in `7781755` inherits the problem: its `warpAffine`-based sweep reads 0.0038 px max
bias where the analytic-rendering measurement gives 0.0166 px (§1.3) — a ~4× understatement.
Fix: analytic rendering of the Gaussian-sum speckle at exactly-deformed coordinates (the
pattern is closed-form, so the deformed image can be evaluated exactly for any invertible
field), plus Gaussian/Poisson noise injection, plus a sub-pixel bias sweep and a noise-floor
test as CI assertions.

**C2 — Keys bicubic interpolation is the accuracy limiter (severity: high).**
Measured peak systematic error ≈ 0.017 px (§1.3). The literature and every leading engine
have moved past cubic convolution: Ncorr uses biquintic B-splines; OpenCorr uses prefiltered
bicubic B-splines (Pan et al., TAML 2016, showing significantly better accuracy than cubic
convolution); VIC-2D exposes optimized 4/6/8-tap spline filters; DICe uses Keys but
advertises its convolution filters as approximating quintic splines. Biquintic B-spline
interpolation typically reduces the peak bias by roughly an order of magnitude
(to ≲ 0.002 px) and is the single highest-leverage accuracy change available.

**C3 — Gradient operator is inconsistent with the interpolant (severity: medium).**
`gradX/gradY` are 2-point central differences, while matching samples through the bicubic.
In IC-GN the converged fixed point satisfies `Σ Jᵀe = 0`, which **does depend on J**: an
inaccurate/inconsistent gradient biases the converged solution, not just the convergence
path. SOTA practice is to take gradients analytically from the same spline representation
used for interpolation (or at least a 5-point/Barron kernel, cf. DICe's
`CONVOLUTION_5_POINT`). This should be fixed together with C2. Note also that at image
borders the clamped-index central difference silently degenerates to a half-scaled one-sided
difference; it is currently masked by the ROI margin but is a trap.

**C4 — Boundary handling is clamp-and-hope (severity: medium).**
`bicubic()` clamps out-of-range taps to the border. The IC-GN bounds check only requires the
*center* of the 4×4 support to lie in `[0, w−1]×[0, h−1]`, so subsets within 2 px of the
border silently sample clamped (repeated-edge) intensities instead of failing or being
flagged. Meanwhile `correlate()` shrinks the ROI by `R + searchRadius + 2` on **all** sides
for **all** points, although `searchRadius` is only needed at the seed — the usable field is
smaller than necessary. Fix: require the full interpolation support inside the image (or use
proper B-spline boundary conditions), and apply the search margin only to seed candidates.

**C5 — Single seed, no retry, propagation can be blocked (severity: medium).**
One fixed seed at the ROI-center grid point: if it fails (decorrelated region, hole in the
pattern, seed on a crack lip), the whole field is empty — there is no fallback. Failed
points are marked `visited` and never retried with a different initial guess, so a closed
band of failures (a crack, a specular highlight) permanently orphans everything behind it.
Also, propagation copies the neighbor's full parameter vector but does not extrapolate the
translation (`u += ux·Δx + uy·Δy`), which shrinks the effective convergence radius at large
strain/step. SOTA (Pan 2009 RG-DIC as implemented in Ncorr/OpenCorr): multiple seeds,
translation prediction, and a retry/second-chance policy.

**C6 — Strain is taken from raw subset gradients (severity: medium, for any real use).**
*Partially addressed by `7781755`.* `ux, uy, vx, vy` from a single subset are the noisiest
outputs of IC-GN (their variance scales ~1/R² worse than displacement). All production tools
compute strain from the **displacement field** via pointwise local least-squares polynomial
fits over a strain window (Pan et al. 2009; DICe's Virtual Strain Gauge post-processor;
VIC-2D's strain filter), with selectable tensor (engineering / Green-Lagrange / principal).
Commit `7781755` added exactly this pattern: a linear PLS plane fit over a configurable
window with Green-Lagrange output (`src/strain.cpp`), verified by `test_strain` and the
demo. Remaining gaps (folded into A6/P5): quadratic-fit option for high strain gradients,
engineering/principal-strain and rotation outputs, VSG-size reporting per iDICs, validation
of the strain *noise* transfer (current tests only check smooth/constant fields), and a
Cholesky solve instead of Cramer's rule in `solve3` for conditioning.

**C7 — Initial guess limited to ±`searchRadius` integer translation (severity: medium).**
Brute-force ZNCC costs O(S²·R²) and the default S=8 px fails for larger motion; there is no
FFT-accelerated cross-correlation (OpenCorr FFTCC), no image-pyramid coarse search, and no
feature-based path (OpenCorr SIFT-aided; DICe feature-matching/phase-correlation/optical-flow
initializers), so large translations and any rotation beyond ~10° (where integer ZNCC
decorrelates) are out of reach.

**C8 — No uncertainty or match-quality outputs (severity: medium for parity).**
VIC-2D reports per-point sigma (1-std confidence from the covariance of the correlation
equations) and rejects matches by confidence margin; DICe outputs per-POI quality metrics.
HL-DIC exposes only ZNCC and iteration count. The covariance `σ² H⁻¹` (with `σ²` estimated
from converged residuals) is nearly free to compute since `H` is already factorized.

**C9 — Solver/interpolation micro-efficiency (severity: low, correctness-neutral).**
`solve6` re-factorizes the *constant* Hessian every iteration (should Cholesky-factorize once
per POI); `bicubic` recomputes kernel weights per sample with no per-image coefficient table
(OpenCorr's global LUT strategy gives large speedups). *Partially addressed by `7781755`*:
an OpenMP path-independent mode parallelizes the POI loop (RG mode remains sequential), but
it re-runs the brute-force integer search at *every* POI — measured only ~2× faster than
sequential RG on 4 cores (`test_parallel`: 250 ms vs 489 ms) because the O(S²R²) search
dominates; A5's FFTCC + A8's LUT/factorization reuse are still needed to reach
OpenCorr-class throughput.

**C10 — Minor I/O and synthetic-generator issues (severity: low).**
`readPGM` does not handle `#` comments and silently misreads `maxval > 255` (16-bit PGM)
files — should validate and reject. `makeSpeckle` clamps to [0,255] which saturates
overlapping speckles into zero-gradient plateaus (mildly reduces local SSSIG). `warpAffine`
does not check `det ≠ 0`. None of these affect the current tests.

### 2.3 Missing subsystems vs a commercial tool

No image formats beyond 8-bit PGM (need 8/12/16-bit TIFF/PNG), no ROI masks or non-square /
conformal subsets, no incremental correlation or reference-update strategy for image
sequences, no lens-distortion correction, no data export or virtual extensometer/strain-gauge
post-processing (PLS strain itself landed in `7781755`), parallelism only via the OpenMP
path-independent mode (`7781755`, ~2× on 4 cores), no GPU. These are catalogued in the
roadmap.

---

## 3. Gap analysis vs leading engines

| Capability | HL-DIC (now) | OpenCorr | DICe (Sandia) | Ncorr | muDIC | VIC-2D (commercial) |
|---|---|---|---|---|---|---|
| Shape function | 1st-order affine | 1st + 2nd order (2D & 3D) | translation/rot/strain/shear toggles (affine + quadratic) | 1st order | FE mesh (global) | subset shape functions, order selectable |
| Optimizer | IC-GN | IC-GN (1st/2nd), NR, IC-LM | gradient-based, simplex (gradient-free), hybrid | IC-GN | global FE least squares | proprietary optimized IC solver |
| Interpolation | Keys bicubic | prefiltered bicubic B-spline (tricubic for DVC) | Keys 4th / convolution filters | biquintic B-spline | B-spline mesh basis | 4/6/8-tap optimized splines |
| Gradients | 2-pt central diff | consistent with spline | finite-diff or 5-pt convolution | spline-consistent | analytic (basis) | proprietary |
| Initial guess | brute-force integer ZNCC at 1 seed | FFTCC, SIFT-aided, epipolar (stereo) | phase correlation, optical flow, feature matching, neighbor values | seed + RG | mesh init | robust proprietary init |
| Propagation | RG (ZNCC heap), single seed, no retry; per-point path-independent mode (`7781755`) | RG multi-seed, path-independent SIFT variant | per-point with initializer fallbacks | RG with multithreaded seeds | n/a (global) | yes |
| Subset weighting | uniform only | uniform | conformal/arbitrary subset shapes, pixel deactivation | subset truncation near discontinuities | n/a | uniform or **Gaussian** (default best) |
| Strain | linear PLS + Green-Lagrange (`7781755`); no quadratic fit / principal / VSG reporting | PLS strain module (2D/3D) | VSG post-processor (window least squares) | least-squares strain windows | direct from FE fields | strain window/filter, tensor options, VSG tool |
| Uncertainty | none | none built-in | per-POI quality metrics (sigma/gamma/beta) | none | none | **sigma confidence margins from covariance** |
| Masks/ROI | rectangle minus margin | ROI + masks | arbitrary conformal subsets, obstructions | arbitrary ROI, holes | mesh on ROI | arbitrary AOI, holes, boundary fill |
| Sequences | single pair | sequence paths | tracking, sequences | sequences (seed propagation) | sequences | incremental correlation, ref update |
| Parallelism | OpenMP in path-independent mode (`7781755`), RG sequential | OpenMP + CUDA (ICGN 2D/3D) | MPI + threads | multithreaded seeds | NumPy vectorized | multi-core, real-time variants |
| Stereo / 3D surface | none | stereo DIC + epipolar + reconstruction | stereo (DICe challenge use) | none | none | VIC-3D product line |
| DVC | none | 3D FFTCC + ICGN3D1 + GPU | no | no | no | VIC-Volume product |
| Self-adaptive subsets | none | example provided (dynamic size/shape per POI) | adaptive refinement of point placement | none | element size choice | n/a (guided by pattern-quality tools) |
| Validation method | synthetic affine (inverse crime) | published papers, DIC Challenge datasets | extensive regression suite, DIC Challenge | paper validation | paper validation | metrological claims (±10 nm class, FOV-dep.) |

Summary: the algorithmic *skeleton* matches SOTA (IC-GN + ZNSSD + RG, and since `7781755` a
first-cut PLS strain module and an OpenMP mode), but HL-DIC currently sits below all four
open engines on interpolation order, shape-function order, initial-guess robustness,
uncertainty, and performance engineering — and below VIC-2D additionally on subset
weighting, confidence margins, incremental correlation, and distortion correction. The DIC Challenge 2.0 datasets (Reu et al., Exp. Mech.) and the
iDICs Good Practices Guide define the acceptance methodology the project should adopt.

---

## 4. Technical roadmap

Ordering below is by dependency, not calendar. Items marked **[P#]** appear in the
prioritized list of §5.

### Phase A — VIC-2D-class accuracy and robustness (2D core)

**A1. Biquintic B-spline interpolation with analytic derivatives [P1]**
- *Where*: `include/dic/interpolation.hpp`, `src/interpolation.cpp`; new
  `BSplineImage` object holding prefiltered coefficients per image.
- *Approach*: Unser's recursive causal/anticausal IIR prefilter (poles of the quintic
  B-spline, mirror boundary conditions) applied separably per row/column once per image;
  evaluation via 6×6 tensor-product kernel; gradients from the analytic derivative of the
  spline (fixes C2 **and** C3 simultaneously — SDI gradients become consistent with the
  sampling model). Keep Keys bicubic as a cheap fallback option behind the same interface.
- *Dependencies/risks*: none external; risk is boundary handling of the prefilter (mirror
  extension) and a ~2× per-sample cost — mitigated by A8's coefficient reuse. Must define
  the valid interpolation domain as `[2, w−3]` to retire the clamping hack (C4).
- *Validation*: Appendix-A bias sweep as a CI test; acceptance in §5-P1. Compare Keys vs
  quintic curves in the docs.

**A2. Honest synthetic validation harness (bias, noise floor, convergence radius) [P2]**
- *Where*: `include/dic/synthetic.hpp`, `src/synthetic.cpp` (analytic deformed-image
  rendering: evaluate the Gaussian sum at `X` solving `X + u(X) = p`, exact for affine and
  Newton-solvable for smooth nonlinear fields; Gaussian/Poisson noise injection; sinusoidal
  and star displacement fields), new tests in `tests/`.
- *Approach*: kill the inverse crime (C1). Add: sub-pixel bias sweep (0→1 px, 21 steps),
  noise-floor Monte-Carlo vs `√2σ/√SSSIG`, convergence-radius probe (initial-guess offset at
  which convergence rate drops below 99%), and a star-pattern/sinusoid spatial-resolution
  test in the style of DIC Challenge 2.0.
- *Dependencies/risks*: none; this precedes and gates every accuracy claim of A1/A3/A4.
- *Validation*: the harness *is* the validation instrument; CI asserts documented bounds.

**A3. Second-order (12-parameter) shape function [P4]**
- *Where*: `include/dic/shape_function.hpp` (add `Params2` and quadratic warp algebra),
  `src/icgn.cpp` (templated or overloaded IC-GN with 12×12 system), `include/dic/linalg.hpp`
  (generalize `solve6` to N×N Cholesky).
- *Approach*: Gao et al. (Opt. Lasers Eng. 2015) ICGN2: quadratic warp
  `x' = x + u + uₓdx + u_y dy + ½u_xx dx² + u_xy dxdy + ½u_yy dy²` (ditto v); quadratic
  warps don't form a group, so use the standard first-order-consistent approximate inverse
  composition (as OpenCorr's ICGN2D2 does). Under-matched shape functions systematically
  bias results where the true field has curvature (Schreier & Sutton 2002; Yu & Pan on
  order selection) — this is required for bending, holes, cracks tips, large heterogeneity.
- *Dependencies/risks*: A2 (needs a heterogeneous-field test to prove benefit); risk is the
  larger, worse-conditioned 12×12 Hessian on low-contrast subsets — mitigate with Cholesky +
  condition check and per-POI fallback to first order.
- *Validation*: sinusoidal field, period ≥ 4 subset widths: expect ≥3× RMS reduction vs
  first order; affine fields must be unchanged within noise.

**A4. Gaussian subset weighting [P8]**
- *Where*: `src/icgn.cpp` (weight w(dx,dy) in `H`, `b`, means and norms — becomes weighted
  ZNSSD), option in `ICGNOptions`.
- *Approach*: center-weighted Gaussian (VIC-2D default: "best combination of spatial
  resolution and displacement resolution"): all sums become weighted; the weighted mean/norm
  keep ZNSSD's illumination invariance.
- *Dependencies/risks*: trivial code; the risk is silently changing the effective spatial
  resolution — must be reported (effective VSG size per iDICs definitions).
- *Validation*: star-pattern test from A2: lower error at high spatial frequency at equal
  noise floor vs uniform weights.

**A5. FFTCC initial guess + multi-seed, retrying reliability propagation [P3]**
- *Where*: new `include/dic/fftcc.hpp`, `src/fftcc.cpp` (dependency-free radix-2 real FFT —
  in-house, ~200 lines), rework of `src/correlation.cpp`.
- *Approach*: (i) per-POI (or per-tile) ZNCC via FFT over a configurable window — removes
  the O(S²R²) brute force and extends capture range to the window size (OpenCorr FFTCC,
  Jiang et al. 2015); (ii) K seeds on a coarse grid, each validated by ZNCC, all pushed into
  the RG heap; (iii) translation prediction when propagating
  (`u_init = u + ux·Δx + uy·Δy`); (iv) failed POIs get a second chance from each new
  neighbor direction and a final integer-search fallback instead of permanent `visited`;
  (v) apply the search margin only at seeds (C4 ROI shrinkage).
- *Dependencies/risks*: FFT correctness (test against brute-force ZNCC); seeds inside
  decorrelated regions must be rejected by threshold, not crash propagation.
- *Validation*: ±30 px translation full-field success without enlarging brute-force search;
  a synthetic decorrelated band (simulated crack/hole) no longer orphans regions; measured
  initial-guess speedup at equal capture range.

**A6. Strain module: pointwise least-squares over strain windows [P5]**
- *Status*: **partially landed in `7781755`** — `include/dic/strain.hpp` / `src/strain.cpp`
  implement the linear PLS plane fit over a window with Green-Lagrange output, skipping
  invalid neighbors, with `test_strain` coverage.
- *Remaining scope*: quadratic-fit option for high strain gradients; engineering, principal
  strains and rotation outputs; report the effective virtual-strain-gauge size
  (`VSG = (M−1)·step + subset`, iDICs) alongside the data; replace the Cramer's-rule
  `solve3` with Cholesky; noise-transfer validation (current tests only cover smooth
  fields). This matches DICe's VSG post-processor and VIC-2D's strain filter (Pan et al.
  2009).
- *Dependencies/risks*: small; window-size selection is a bias/noise tradeoff that must be
  a documented user parameter, not a constant.
- *Validation*: constant-strain recovery < 2e-5 absolute (partially covered); sinusoidal
  field with analytic strain: measured window-dependent attenuation matches the PLS transfer
  function; strain noise floor vs theory within 30%.

**A7. Uncertainty quantification and match-quality outputs [P7]**
- *Where*: `src/icgn.cpp` (+ result fields), `include/dic/correlation.hpp` (per-POI sigma,
  SSSIG, residual), post-filter in `src/correlation.cpp`.
- *Approach*: per-POI covariance `σ̂²·H⁻¹` with `σ̂²` from converged ZNSSD residuals →
  `sigma_u`, `sigma_v` (VIC-2D's "sigma"/confidence margin); pattern matchability via SSSIG
  (Pan 2008) per subset; optional confidence-margin rejection replacing/complementing the
  bare ZNCC threshold.
- *Dependencies/risks*: cheap (H already factorized). Risk: covariance is only valid near
  convergence — gate on `converged`.
- *Validation*: Monte-Carlo over ≥100 noise realizations: predicted vs empirical std within
  25%; injected decorrelated subsets get rejected by margin.

**A8. Performance engineering: threading, coefficient LUT, factorization reuse [P6]**
- *Status*: **partially landed in `7781755`** — OpenMP path-independent mode parallelizes
  the POI loop (`DICOptions::pathIndependent`). But each POI re-runs the O(S²R²)
  brute-force integer search, so the measured gain is only ~2× on 4 cores
  (`test_parallel`), and RG mode remains sequential.
- *Remaining scope*: replace the per-POI brute-force init with A5's FFTCC (or
  neighbor-seeded init) in path-independent mode; per-image spline coefficient table
  (from A1) in `src/interpolation.cpp`; Cholesky-factorize `H` once per POI and reuse
  across iterations in `src/icgn.cpp` (C9); tile-based multi-seed RG so reliability-guided
  mode also parallelizes.
- *Dependencies/risks*: RG is inherently sequential — the tile/two-pass redesign changes
  propagation semantics; must verify identical results on well-conditioned fields.
- *Validation*: ≥6× throughput on 8 cores on the 512² demo vs sequential RG; results within
  1e-10 px of single-thread; report POI/s (target ≥ 20 000 POI/s multithreaded,
  OpenCorr-class).

### Phase B — Exceeding VIC-2D (2D)

**B1. ROI masks, conformal/partial subsets.** Arbitrary-shape ROIs with holes
(bitmask); per-subset pixel deactivation with weighted ZNSSD renormalization (DICe-style
conformal subsets; Ncorr-style truncation at discontinuities). *Where*: `Image`-side mask +
`icgn.cpp`. *Validate*: crack-field synthetic — error localized to the crack line only.

**B2. Self-adaptive subsets.** Grow/shape each subset until SSSIG exceeds a threshold
(Pan-style self-adaptive DIC; OpenCorr ships an example). Depends on A7's SSSIG. *Validate*:
spatially varying pattern quality — uniform noise floor across the field.

**B3. Sequences: incremental correlation + reference-update strategy.** Chain
ref→…→frame k with automatic re-reference when ZNCC/sigma degrades; error-accumulation
control (compose warps, not just translations); rigid-body-motion removal post-process.
*Where*: new `sequence.hpp/cpp` orchestrator. *Validate*: 100-frame synthetic ramp to 50%
strain with pattern breakdown; compare accumulated vs direct error.

**B4. Large-deformation path: pyramids + feature-aided init.** Image pyramid coarse-to-fine
initial guess; in-house SIFT-like detector/descriptor (or DISFlow-style variational init)
feeding per-POI affine estimates via local RANSAC (OpenCorr SIFT-aided, path-independent).
*Validate*: 30° rotation + 30% strain cases that defeat integer ZNCC.

**B5. Image I/O and export.** 8/12/16-bit TIFF (vendored minimal reader or libtiff behind an
option), PNG via vendored stb-style decoder, CSV/VTK/NPZ-like export of fields. Keep the
core dependency-free by vendoring. *Validate*: round-trip tests, 16-bit noise-floor test
(quantization at 8-bit currently inflates σ).

**B6. Robustness options.** IC-LM (Levenberg-Marquardt damping) fallback when IC-GN
diverges (OpenCorr added ICLM); optional Gaussian pre-filter to reduce noise-induced and
interpolation bias (Pan's pre-filtering result); divergence guard (ZNCC-decrease detection).
*Validate*: convergence-rate maps vs initial-guess error, low-contrast/low-quality pattern
suite.

**B7. Global (FE) DIC option.** Q4 mesh global least squares with Tikhonov regularization
(muDIC/Correli-style) sharing the interpolation and synthetic stack — valuable for
continuity-constrained fields and as a cross-check on local DIC; also addresses the
saddle-point issues DICe's global mode targets. Big item; optional for parity, differentiator
beyond it.

**B8. GPU backend (CUDA or SYCL) for batch IC-GN.** Deferred until A8's structure exists;
mandatory groundwork for DVC at scale (OpenCorr GPU ICGN precedent).

### Phase C — VIC-3D: stereo DIC

**C1. Camera model + planar calibration + bundle adjustment.**
- *Where*: new `include/dic/calib/` (`camera.hpp`, `homography.hpp`, `calibrate.hpp`,
  `lm.hpp`), `src/calib/`.
- *Approach*: pinhole intrinsics (fx, fy, cx, cy, skew) + Brown–Conrady distortion
  (k1,k2,k3,p1,p2); checkerboard corner detection (Harris + gradient-based saddle-point
  sub-pixel refinement — DIC-grade corners); Zhang (2000): DLT homographies per view →
  closed-form intrinsics → per-camera LM refinement → stereo extrinsics (R, t) initialized
  from the essential matrix and refined by **joint bundle adjustment** over all calibration
  frames (minimize total reprojection error over intrinsics, distortion, extrinsics, board
  poses). Requires a small dense Levenberg–Marquardt solver + Cholesky/QR in `linalg`
  (extend the existing 6×6 to general N — also used by A3/A6).
- *Dependencies/risks*: corner detector robustness on real images is the main risk; the
  optimizer is small-scale (≤ a few hundred parameters, dense normal equations are fine).
  Lens-distortion module doubles as VIC-2D-parity distortion correction for 2D measurements.
- *Validation*: synthetically rendered boards with known K/D/R/t (reuse the analytic
  renderer + projective warp): recover parameters to tight tolerance, reprojection RMS
  < 0.02 px synthetic; on real captures < 0.05 px and stable across re-runs.

**C2. Stereo (cross-camera) matching with epipolar constraint.**
- *Where*: `include/dic/stereo.hpp`, `src/stereo.cpp`, reusing the 2D IC-GN wholesale.
- *Approach*: match camera-0 reference → camera-1 reference (disparity `q`) and camera-0
  deformed → camera-1 deformed. Initial guess: 1D search along the epipolar line (band ±1–2
  px for calibration error), or rectification + FFTCC per A5; IC-GN with affine (upgrade to
  A3 quadratic for strong perspective/foreshortening — this is where 2nd order pays off).
  Reject by epipolar residual + ZNCC (OpenCorr's epipolar-constraint-aided matching).
- *Dependencies/risks*: C1 accuracy bounds everything; perspective distortion between wide-
  baseline views is the risk — mitigated by A3 and seed transfer from SIFT features (B4).
- *Validation*: synthetic stereo pair of a plane at known pose: disparity error < 0.02 px;
  reconstructed plane flatness (see C3).

**C3. Temporal chain + triangulation + 3D displacement.**
- *Where*: `src/stereo.cpp`, `include/dic/reconstruct.hpp`.
- *Approach*: per-POI correspondences from (i) temporal 2D DIC in camera 0 (existing engine)
  and (ii) stereo matching at t0 and tk; triangulate by linear DLT then refine each point by
  minimizing reprojection (Hartley–Sturm optimal or 2-view LM); 3D displacement
  `ΔX = X(tk) − X(t0)` in the world frame; optional per-frame extrinsics re-estimation
  (camera-motion compensation) as a small bundle adjustment over rigid outliers.
- *Dependencies/risks*: error propagation from four correlation fields — needs A7 sigma to
  weight triangulation; risk of correspondence-chain drift → validate composition vs direct
  matching.
- *Validation*: synthetic rigid-body translations/rotations of a 3D speckled surface
  rendered into both cameras (extend `synthetic` with a projective surface renderer):
  3D displacement RMS < 1/50 000 of FOV (VIC-3D-class); flatness/shape error on known
  geometry; then Stereo-DIC Challenge datasets.

**C4. Surface strain on the reconstructed manifold.**
- *Approach*: local tangent-plane fit per POI neighborhood; project 3D displacements into
  the local frame; run the A6 PLS machinery in 2D surface coordinates → Green-Lagrange
  surface strain (VIC-3D behavior). *Validate*: inflation-of-a-plate analytic field;
  zero-strain rigid motions to machine noise.

### Phase D — VIC-Volume: digital volume correlation

**D1. Volume infrastructure.** `include/dic/volume.hpp`: strided 3D `float` container
(double is prohibitive at 1024³ = 4 GiB float), raw/TIFF-stack I/O, sub-volume views for
out-of-core tiling. *Risk*: memory bandwidth dominates everything downstream — design for
tile locality now.

**D2. Tricubic (then triquintic) B-spline interpolation.** Separable Unser prefilter along
x/y/z (direct reuse of A1's 1D routines); analytic gradients. OpenCorr uses tricubic
B-spline (Yang et al. 2021); triquintic as a later accuracy option. *Validate*: 3D analytic
Gaussian-blob volume, trilinear-vs-tricubic bias sweep (Appendix-A methodology in 3D).

**D3. 3D IC-GN with 12-parameter affine shape function.** `u,v,w` + 9 gradients; 12×12
Cholesky (shared with A3's generalized solver); 3D FFTCC integer guess (radix-2 3D FFT from
A5's kernels); reliability-guided propagation over the 6-connected POI lattice. This is
OpenCorr ICGN3D1 / Bar-Kochba FIDVC territory. *Risks*: subset 31³ ≈ 30k voxels × iterations
— A8 threading and (eventually B8 GPU) are prerequisites for practical volumes; conditioning
of low-texture tomography subsets → A7-style SSSIG gating in 3D.
*Validate*: synthetic volumes under affine + harmonic fields (noise-free and Gaussian/CT-like
noise): displacement bias < 0.005 vx, noise floor documented; zero-displacement repeat scans
for the real noise floor; published DVC benchmark volumes (e.g., FIDVC sample data).

**D4. 3D strain.** A6's PLS in three dimensions over cubic windows → full 3D strain tensor;
visualization export (VTK). *Validate*: constant-strain volumes to < 5e-5; compression-of-
a-sphere analytic field.

**D5. Tomography-specific robustness.** Ring/beam-hardening artifact tolerance (masked
subsets from B1 in 3D), intensity drift between scans (ZNSSD already covers linear terms),
self-adaptive subset radius in low-texture regions (B2 in 3D).

---

## 5. Prioritized next implementations (highest leverage first)

**P1. Biquintic B-spline interpolation + spline-consistent analytic gradients (A1).**
*Acceptance*: on the Appendix-A analytic sweep, peak |mean bias| ≤ 0.002 px noise-free
(currently 0.0166 px); no regression in `test_correlation`; per-POI runtime within 2× of
Keys after coefficient caching; Keys retained behind the same interface and covered by tests.

**P2. Honest validation harness — analytic rendering, noise, bias/noise-floor CI tests (A2).**
*Acceptance*: `warpAffine`-based tests replaced/augmented by analytic-rendering tests; new
ctest targets assert (i) peak sub-pixel bias below the P1 bound, (ii) noise floor within 25%
of `√2σ/√SSSIG`, (iii) convergence radius ≥ 0.5 subset width for translation; README
accuracy claims updated to non-inverse-crime numbers.

**P3. FFTCC initial guess + multi-seed retrying propagation (A5).**
*Acceptance*: full-field success on a ±30 px translation with no brute-force search-radius
increase; a synthetic decorrelated band no longer orphans any reachable region (coverage
= 100% of correlatable POIs); seed failure auto-recovers via alternate seeds; initial-guess
cost at equal capture range reduced ≥ 10× vs brute force (measured).

**P4. Second-order (12-parameter) shape function (A3).**
*Acceptance*: sinusoidal field with period 4× subset width: RMS displacement error ≥ 3×
lower than first order at equal subset size; affine-field results unchanged within 1e-4 px;
automatic fallback to first order on ill-conditioned subsets, with a per-POI flag.

**P5. Complete the pointwise least-squares strain module (A6; core landed in `7781755`).**
*Acceptance for the remaining scope*: constant strain recovered to < 2e-5 absolute from a
**noisy** displacement field; strain noise vs window size matches PLS theory within 30%;
outputs engineering and principal strains + rotation in addition to Green-Lagrange;
reported VSG size per iDICs; `solve3` replaced by Cholesky.

**P6. Finish performance engineering: fast init in parallel mode, coefficient table,
Cholesky reuse (A8; OpenMP loop landed in `7781755`).**
*Acceptance*: ≥ 6× throughput on 8 cores for the 512² demo vs sequential RG (target
≥ 20 000 POI/s; currently ~2× on 4 cores because the per-POI brute-force integer search
dominates); results within 1e-10 px of single-threaded; Hessian factorized once per POI
(verified by profile).

**P7. Per-POI uncertainty and quality outputs (A7).**
*Acceptance*: sigma from `σ̂²H⁻¹` validated by Monte-Carlo (≥100 noise realizations,
predicted vs empirical std within 25%); SSSIG exposed per POI; confidence-margin rejection
demonstrably filters injected bad matches that the ZNCC threshold misses.

**P8. Gaussian subset weighting (A4).**
*Acceptance*: star/sinusoid spatial-resolution test shows lower error at high spatial
frequency at equal noise floor vs uniform weights; weighting selectable per run; default
choice documented with the measured tradeoff.

---

## 6. References (grounding for the claims above)

- Baker, Matthews, *Lucas-Kanade 20 Years On*, IJCV 2004 — IC formulation.
- Pan, Li, Tong, *Fast, robust and accurate DIC using IC-GN*, and Pan 2009 *Reliability-
  guided DIC*; Pan 2018 review, *Meas. Sci. Technol.* — IC-GN/ZNSSD/RG canon.
- Schreier, Braasch, Sutton, *Systematic errors in DIC caused by intensity interpolation*,
  Opt. Eng. 2000; Schreier & Sutton 2002 (undermatched shape functions).
- Pan et al., TAML 2016 — bicubic B-spline vs bicubic convolution (OpenCorr's basis).
- Gao et al., Opt. Lasers Eng. 2015 — second-order IC-GN (ICGN2).
- Pan, Xie et al. 2008 — SSSIG subset-size criterion; Wang/Pan noise-floor analysis.
- Jiang et al. 2015 (FFTCC); Yang et al. 2020/2021 (SIFT-aided path-independent DIC, 3D
  SIFT DVC, tricubic B-spline); Jiang, *OpenCorr*, Opt. Lasers Eng. 2023.
- Turner, *DICe Reference Manual*, SAND2015-10606; DICe docs (conformal subsets, simplex,
  VSG post-processor, initializers).
- Blaber, Adair, Antoniou, *Ncorr*, Exp. Mech. 2015 — biquintic B-spline, RG.
- Olufsen et al., *muDIC*, SoftwareX 2020 — FE-based global DIC.
- Reu et al., *DIC Challenge* & *DIC Challenge 2.0*, Exp. Mech. — validation datasets/star
  patterns; iDICs *Good Practices Guide* 2018 — VSG definitions, reporting.
- Correlated Solutions VIC-2D documentation — 4/6/8-tap splines, Gaussian subset weights,
  incremental correlation, confidence margins (sigma), strain window, distortion correction.
- Zhang, *A flexible new technique for camera calibration*, TPAMI 2000; Hartley & Sturm,
  *Triangulation*, CVIU 1997 — Phase C.
- Bar-Kochba et al., *FIDVC*, Exp. Mech. 2015; Buljac et al., *DVC review*, Exp. Mech. 2018
  — Phase D.

---

## Appendix A — Audit harness (bias sweep & noise floor)

Not part of the engine; compile standalone against `libdic` to reproduce §1.3:
`g++ -O3 -std=c++17 -I include bias_sweep.cpp -L build -ldic -o bias_sweep`.

```cpp
// Measures true sub-pixel interpolation bias by rendering speckle ANALYTICALLY
// (Gaussian sum evaluated at exactly shifted coordinates) - no inverse crime.
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>
#include "dic/icgn.hpp"
#include "dic/image.hpp"

using namespace dic;
struct Speckle { double cx, cy, sigma; };

static Image renderAnalytic(int W, int H, const std::vector<Speckle>& sp,
                            double shiftX, double shiftY, double bg, double amp,
                            double noiseSigma, uint32_t noiseSeed) {
  Image img(W, H);
  for (double& v : img.data) v = bg;
  for (const Speckle& s : sp) {
    const double cx = s.cx + shiftX, cy = s.cy + shiftY;
    const double inv2s2 = 1.0 / (2.0 * s.sigma * s.sigma);
    const int r = static_cast<int>(std::ceil(4.0 * s.sigma));
    const int x0 = std::max(0, static_cast<int>(cx) - r);
    const int x1 = std::min(W - 1, static_cast<int>(cx) + r);
    const int y0 = std::max(0, static_cast<int>(cy) - r);
    const int y1 = std::min(H - 1, static_cast<int>(cy) + r);
    for (int y = y0; y <= y1; ++y)
      for (int x = x0; x <= x1; ++x) {
        const double dx = x - cx, dy = y - cy;
        img.at(x, y) += amp * std::exp(-(dx * dx + dy * dy) * inv2s2);
      }
  }
  if (noiseSigma > 0.0) {
    std::mt19937 rng(noiseSeed);
    std::normal_distribution<double> nd(0.0, noiseSigma);
    for (double& v : img.data) v += nd(rng);
  }
  return img;
}

int main() {
  const int W = 256, H = 256;
  std::mt19937 rng(99u);
  std::uniform_real_distribution<double> ux(0.0, W - 1.0), uy(0.0, H - 1.0);
  std::uniform_real_distribution<double> ur(0.9, 1.5);
  std::vector<Speckle> sp;
  for (int i = 0; i < 9000; ++i) sp.push_back({ux(rng), uy(rng), ur(rng)});
  const Image ref = renderAnalytic(W, H, sp, 0, 0, 20.0, 120.0, 0.0, 0);

  ICGNOptions opt;
  opt.subsetRadius = 15; opt.maxIterations = 100; opt.convergenceTol = 1e-6;
  std::vector<std::pair<int, int>> pois;
  for (int y = 60; y <= 196; y += 34)
    for (int x = 60; x <= 196; x += 34) pois.push_back({x, y});

  std::printf("shift  meanBias  stdAcrossPOI\n");
  for (int k = 0; k <= 20; ++k) {
    const double shift = 0.05 * k;
    const Image def = renderAnalytic(W, H, sp, shift, 0, 20.0, 120.0, 0.0, 0);
    double sum = 0, sum2 = 0; int n = 0;
    for (auto [x, y] : pois) {
      Params init; init.u = std::floor(shift + 0.5);
      const ICGNResult r = icgnMatch(ref, def, x, y, init, opt);
      if (!r.converged) continue;
      const double e = r.params.u - shift;
      sum += e; sum2 += e * e; ++n;
    }
    const double mean = sum / n;
    std::printf("%5.2f %9.6f %9.6f (n=%d)\n", shift, mean,
                std::sqrt(std::max(0.0, sum2 / n - mean * mean)), n);
  }
  // Noise floor: shift 0.5, sigma=2 gray on both images, 12 trials x 25 POIs.
  std::vector<double> errs;
  for (uint32_t t = 0; t < 12; ++t) {
    const Image rN = renderAnalytic(W, H, sp, 0, 0, 20.0, 120.0, 2.0, 1000 + t);
    const Image dN = renderAnalytic(W, H, sp, 0.5, 0, 20.0, 120.0, 2.0, 5000 + t);
    for (auto [x, y] : pois) {
      Params init; init.u = 1.0;
      const ICGNResult r = icgnMatch(rN, dN, x, y, init, opt);
      if (r.converged) errs.push_back(r.params.u - 0.5);
    }
  }
  double m = 0; for (double e : errs) m += e; m /= errs.size();
  double v = 0; for (double e : errs) v += (e - m) * (e - m); v /= errs.size();
  std::printf("noise floor: n=%zu mean=%.5f std=%.5f px\n", errs.size(), m, std::sqrt(v));
  return 0;
}
```
