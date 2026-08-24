# 激光测振跟踪滤波设计包

本目录汇总本次 Cloud Agent 完成的**零差光 IQ**与**外差电 IQ（Polytec 类）**跟踪滤波设计与仿真验证。

## 目录说明

| 文件夹 | 体制 | 说明 |
|--------|------|------|
| `homodyne_tracking_design/` | **零差光 IQ** | 1550 nm，分档 SLOW/MEDIUM/FAST，等纹波 ζ=2.65，载波 PLL + 公共 4 MHz 残差窗 |
| `heterodyne_tracking_design/` | **外差电 IQ** | HeNe 632.8 nm，量程→加速度→fn，纯 NCO（无残差窗） |

## 快速开始

```bash
pip install numpy

# 零差验证
cd homodyne_tracking_design && python validate_tracking.py

# 外差验证
cd heterodyne_tracking_design && python validate_heterodyne.py
```

## 你的使用场景（参考）

- 日常振动 **< 100 kHz** → 零差 **SLOW** 档
- 偶尔测到 **3 MHz** → 零差升 **FAST** 档
- 外差 Polytec 类 → 按**速度量程 + 振动频率**选档（见 `heterodyne_tracking_design/README.md`）

## 原始研究包

你上传的 `p跟踪.7z`（MATLAB 文档 + 原仿真）**不在本仓库内**，请自行保留；本包是在其基础上的**新设计与 Python 验证**。

## 来源

GitHub: https://github.com/9997433-bit/HL  
分支: `cursor/tracking-filter-bundle-075a`
