# 1550 nm 零差 IQ 分档跟踪滤波设计

基于 Polytec 概念仿真的改进方案：**按目标频段独立优化 `fn`**，不再使用 `fn = f_max / 2.808` 的等边缘规则。

## 系统参数

| 参数 | 值 |
|------|-----|
| 波长 | 1550 nm |
| 采样率 | 250 MS/s |
| 前端噪声带宽 | 40 MHz（双边 ENBW） |
| 环路阻尼 | ζ = 1.2 |

## 三档设计

| 档位 | 目标频段 | fn | B_loop | 弱光 SNR 增益* | 3 MHz 幅值误差 |
|------|----------|-----|--------|----------------|----------------|
| SLOW | ≤ 100 kHz | 80 kHz | 0.35 MHz | **+37 dB** @100 kHz | N/A |
| MEDIUM | ≤ 1 MHz | 680 kHz | 3.0 MHz | **+18 dB** @1 MHz | N/A |
| FAST | ≤ 3 MHz | 1.85 MHz | 8.2 MHz | **+6 dB** @3 MHz | **2.6%** |

\* CNR = 3 dB，B_frontend = 40 MHz，蒙特卡洛中值

## 相对旧方案的核心改进

旧方案 `fn = f_max/2.808` 令 FAST 档 fn ≈ 1.07 MHz，导致 3 MHz 处幅值误差 **~28%**。

新方案 FAST fn = 1.85 MHz，3 MHz 幅值误差 **2.6%**，弱光仍有 **+6 dB** SNR 改善。

## 档位选择规则

```python
from design_params import select_band, BANDS

band = select_band(f_target_hz)   # 'SLOW' | 'MEDIUM' | 'FAST'
fn = BANDS[band]['fn']
```

按**目标振动频率**选档，而非按速度量程。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py
```

全部断言应显示 `PASS`。

## 文件

- `design_params.py` — 参数表与选档逻辑
- `core.py` — PLL 内核（移植自原项目）
- `validate_tracking.py` — V1–V5 仿真验证
