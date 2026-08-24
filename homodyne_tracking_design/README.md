# 1550 nm 零差 IQ 分档跟踪滤波设计

等纹波方案：**ζ = 2.65**，各档带内幅值误差 ≤ 3%，`fn = f_max / 1.875`。

## 系统参数

| 参数 | 值 |
|------|-----|
| 波长 | 1550 nm |
| 采样率 | 250 MS/s |
| 前端噪声带宽 | 40 MHz（双边 ENBW） |
| 环路阻尼 | **ζ = 2.65**（等纹波，抑制旧方案 +11% 带内峰化） |

## 三档设计

| 档位 | 目标频段 | fn | B_loop | 弱光 SNR 增益* |
|------|----------|-----|--------|----------------|
| SLOW | ≤ 200 kHz | 110 kHz | 0.96 MHz | **+35 dB** @100 kHz |
| MEDIUM | ≤ 1 MHz | 530 kHz | 4.7 MHz | **+17 dB** @1 MHz |
| FAST | ≤ 3 MHz | 1.60 MHz | 15.5 MHz | +2 dB @3 MHz |

\* CNR = 3 dB，B_frontend = 40 MHz，蒙特卡洛中值

## ≤100 kHz 振动专用（推荐）

若仪器只测 **100 kHz 以内**，固定 SLOW 档即可，无需切档：

```python
from design_params import APP_100KHZ, recommended_for_app

cfg = APP_100KHZ          # fn=110 kHz, zeta=2.65
# 或
cfg = recommended_for_app(f_max_hz=100e3)
```

预期：弱光 SNR 改善 **~35 dB**，100 kHz 幅值误差 **< 3%**。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py
```

## 文件

- `design_params.py` — 参数表、选档逻辑、`APP_100KHZ` 单档快捷配置
- `core.py` — PLL 内核
- `validate_tracking.py` — 仿真验证（9/9 PASS）
- `设计方案.md` — 完整推导
