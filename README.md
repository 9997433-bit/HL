# HL-DIC

A dependency-free **C++17** Digital Image Correlation (DIC) engine — the algorithmic
core for a commercial-grade full-field deformation measurement suite in the spirit of
Correlated Solutions' VIC-2D / VIC-3D / VIC-Volume. This repository currently
implements the **2D DIC** core (the foundation of VIC-2D).

## Why C++ (not Python)

Commercial DIC/DVC tools (Correlated Solutions VIC, Sandia's [DICe](https://github.com/dicengine/dice),
[OpenCorr](https://github.com/vincentjzy/OpenCorr)) are built on native, compiled cores for
performance, numerical stability, and dependency-free deployment. HL-DIC follows the same
approach: the engine uses **only the C++ standard library** — no third-party runtime.

## Algorithm

The engine matches the state of the art used by OpenCorr and DICe:

- **Subset-based local DIC** with a **first-order (affine) shape function** (6 parameters:
  `u, ux, uy, v, vx, vy`).
- **Inverse-Compositional Gauss-Newton (IC-GN)** optimizer minimizing the **ZNSSD**
  criterion (robust to linear illumination changes); the Hessian is precomputed from the
  reference subset (the inverse-compositional advantage).
- **Bicubic (Keys) convolution interpolation** for sub-pixel intensity sampling.
- **Integer-pixel ZNCC search** for the seed initial guess, followed by
  **reliability-guided (ZNCC-ordered) propagation** across the point grid.
- Per-point deformation gradients (`ux, uy, vx, vy`) give the local **strain** directly.

## Build & test

Requires a C++17 compiler and CMake (>= 3.16). No external libraries.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build --output-on-failure
```

## Demo

```bash
./build/dic_demo /tmp/dic_out
```

Generates a synthetic speckle pair under a known affine deformation, runs full-field
correlation, prints the recovered-vs-ground-truth accuracy, and writes displacement-field
heatmaps (`u_field.ppm`, `v_field.ppm`) plus the speckle images.

## Layout

```
include/dic/    Public headers (image, interpolation, shape function, IC-GN, correlation, synthetic)
src/            Engine implementation
apps/dic_demo   Synthetic end-to-end demo with quantitative validation
tests/          CTest suite (linalg, interpolation, IC-GN accuracy, full-field accuracy)
```

## Roadmap toward VIC-3D / VIC-Volume

- **Accuracy/robustness**: 2nd-order shape function, biquintic B-spline interpolation,
  FFT-based initial guess (FFTCC), SIFT/feature-guided affine for large deformation.
- **Performance**: OpenMP multithreading and optional GPU (CUDA) IC-GN.
- **I/O**: TIFF/PNG image loading, results export.
- **VIC-3D**: stereo camera calibration, epipolar-constrained matching, 3D reconstruction.
- **VIC-Volume**: Digital Volume Correlation (DVC) on 3D tomographic data.
