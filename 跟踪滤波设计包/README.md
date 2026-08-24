# 激光测振跟踪滤波设计包

本目录汇总本次 Cloud Agent 完成的激光测振**四类研究**：外差跟踪、零差跟踪、椭圆校正、QTec 多路散斑分集。

## 四类研究

| # | 研究方向 | 位置 | 说明 |
|---|----------|------|------|
| 1 | **外差跟踪** | `heterodyne_tracking_design/` | 外差电 IQ（Polytec 类），HeNe 632.8 nm，量程→加速度→fn，纯 NCO（无残差窗） |
| 2 | **零差跟踪** | `homodyne_tracking_design/` | 零差光 IQ，1550 nm，分档 SLOW/MEDIUM/FAST，ζ=1.2，载波 PLL + 公共 4 MHz 残差窗 |
| 3 | **椭圆校正** | `homodyne_tracking_design/`（`ellipse_correction.py`、`calibrate_ellipse.py`、`validate_ellipse_*.py`、`椭圆标定操作指南.md`） | 零差 IQ 通道失配（g、δ、p、q）的 Heydemann 校正：出厂标定 + 在线偏置跟踪，与零差跟踪共用目录 |
| 4 | **QTec 多路散斑分集** | `qtec_diversity_design/` | M 路独立散斑接收，每路 PLL/FM 鉴频 + 块式 SNR 加权速度域合成（P0+P1 已验证，10/10 断言 PASS；P2–P4 见其 README 路线图） |

## 快速开始

```bash
pip install numpy

# 1 外差验证
cd heterodyne_tracking_design && python validate_heterodyne.py

# 2 零差验证
cd homodyne_tracking_design && python validate_tracking.py

# 3 椭圆校正验证
cd homodyne_tracking_design && python validate_ellipse_small_disp.py

# 4 QTec 分集验证（P0+P1）
cd qtec_diversity_design && python validate_diversity_p0_p1.py
```

## 椭圆标定（零差 IQ）

- **操作指南**：`homodyne_tracking_design/椭圆标定操作指南.md`（出厂标定 g,δ + 在线 p,q）
- **标定工具**：`python calibrate_ellipse.py --csv your_iq.csv --out ellipse_cal.json`
- **无需大振动**：g,δ 出厂标定一次；日常换表面/距离只在线跟踪偏置

## 你的使用场景（参考）

- 日常振动 **< 100 kHz** → 零差 **SLOW** 档
- 偶尔测到 **3 MHz**(小振幅)→ 仍用 **SLOW** 档:测量带宽由公共 4 MHz 残差窗保证,与档位无关(守卫先行选档,`select_band(3 MHz, 20 mm/s)` = SLOW);只有大动态(φ_err 守卫超限)才自动升 MEDIUM/FAST
- 外差 Polytec 类 → 按**速度量程 + 振动频率**选档（见 `heterodyne_tracking_design/README.md`）
- 粗糙表面**散斑掉光**频繁 → QTec 多路分集（M=3 时联合掉光 ~p³，见 `qtec_diversity_design/README.md`）

## 原始研究包

你上传的 `p跟踪.7z`（MATLAB 文档 + 原仿真）**不在本仓库内**，请自行保留；本包是在其基础上的**新设计与 Python 验证**。

## 来源

GitHub: https://github.com/9997433-bit/HL  
分支: `cursor/tracking-filter-bundle-075a`
