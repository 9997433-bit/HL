# 1550 nm 零差 IQ 分档跟踪滤波设计

等纹波方案：**ζ = 2.65**，各档带内幅值误差 ≤ 3%。

## 系统参数

| 参数 | 值 |
|------|-----|
| 波长 | 1550 nm |
| 采样率 | 250 MS/s |
| 前端噪声带宽 | 40 MHz（双边 ENBW） |
| 环路阻尼 | **ζ = 2.65** |

## 三档设计

| 档位 | 覆盖频段 | fn | 弱光 SNR 增益* | 适用场景 |
|------|----------|-----|----------------|----------|
| **SLOW** | ≤ 200 kHz | 110 kHz | **+35 dB** @100 kHz | 日常/结构振动（**你的主场景**） |
| **MEDIUM** | ≤ 1 MHz | 530 kHz | **+17 dB** @1 MHz | 中等频率抽查 |
| **FAST** | ≤ 3 MHz | 1.60 MHz | +2 dB @3 MHz | 最高 3 MHz 测量 |

\* CNR = 3 dB，B_frontend = 40 MHz

## 你的场景：大部分 <100 kHz，最大 3 MHz

**保留三档，默认 SLOW，按当前测量频率升档。**

| 当前目标频率 | 选用档位 | 说明 |
|-------------|----------|------|
| 日常 ≤ 100 kHz | **SLOW** | 灵敏度最高，+35 dB 弱光收益 |
| 200 kHz – 1 MHz | MEDIUM | 自动或手动升档 |
| 1 MHz – 3 MHz | FAST | 保证 3 MHz 幅值 <3% |

```python
from design_params import APP_HYBRID, cfg_for_frequency

# 开机默认
band = APP_HYBRID['default_band']          # 'SLOW'
cfg = cfg_for_frequency(50e3)              # 日常 50 kHz -> SLOW

# 切换到 3 MHz 超声测量
cfg = cfg_for_frequency(3e6, current_band=band)  # -> FAST, fn=1.60 MHz

# 测完回到结构振动（带迟滞，避免边界抖动）
cfg = cfg_for_frequency(80e3, current_band='FAST')  # 仍 FAST 直到 <150 kHz
cfg = cfg_for_frequency(80e3, current_band=cfg['band'])  # -> 回落 SLOW
```

迟滞边界：SLOW↔MEDIUM 在 150/200 kHz；MEDIUM↔FAST 在 800 kHz/1 MHz。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py
```

## 文件

- `design_params.py` — 三档参数、`APP_HYBRID`、`cfg_for_frequency()`
- `core.py` — PLL 内核
- `validate_tracking.py` — 仿真验证（9/9 PASS）
