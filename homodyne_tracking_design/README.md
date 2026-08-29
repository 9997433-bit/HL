# 1550 nm 零差 IQ 分档跟踪滤波设计与验证

基于原项目 `core.py`(`pll_carrier_regen` / 残差窗)的三档跟踪滤波方案及完整仿真验证。

## 架构(每档双路径)

- **载波路径**:PLL 载波再生(分档 fn,ζ=2.65 等纹波),纯 NCO 输出 —— 提供弱光门限扩展与掉落飞轮。
- **测量路径**:公共残差窗 —— `r = z·e^{-jφ}` 经线性相位 FIR(截止 **B_win = 4 MHz**)后重构 `y = e^{jφ}·e^{j·gs·angle(LP(r))}`。窗跟随 NCO 居中,**任何档测量带宽都是 DC–4 MHz**,换档只改变载波环动态。

关键实测规律:点击(click)清除发生在复域残差窗内,要求 **B_loop < B_win**。SLOW/MEDIUM 满足,低频 SNR 增益吃满门限扩展;FAST 档(B_loop=13.8 MHz)NCO 把部分点击跟进输出,低频增益仅 ~+2.5 dB —— 低频目标必须用低档(选档逻辑保证)。

## 系统参数

| 参数 | 值 |
|------|-----|
| 波长 | 1550 nm |
| 采样率 | 250 MS/s |
| 前端噪声带宽 | 40 MHz(双边 ENBW) |
| 环路阻尼 | ζ = 2.65(NCO 路径等纹波 ±3%) |
| 残差测量窗 | 4 MHz FIR,1025 taps(三档公共) |

## 三档设计与实测(CNR=3 dB, B_frontend=40 MHz, 12 seeds 中值)

| 档位 | 目标频段 | fn | B_loop | SNR 增益(设计频点) | 3 MHz 幅值误差(全输出) |
|------|----------|-----|--------|----------------------|--------------------------|
| SLOW | ≤ 200 kHz | 110 kHz | 0.95 MHz | **+38.5 dB** @100 kHz | +0.06% |
| MEDIUM | ≤ 1 MHz | 530 kHz | 4.6 MHz | **+18.6 dB** @1 MHz | +0.03% |
| FAST | ≤ 3 MHz | 1.60 MHz | 13.8 MHz | **+2.2 dB** @3 MHz | −0.00% |

## PLL 价值边界(V2,与固定复数低通对照)

- 静止/小摆动载波:固定 LP 与正确选档的跟踪档增益打平(+37.2 vs +37.2 dB)—— **PLL 无增值**。
- 大 Doppler 摆动(fD=7.7 MHz > B_win):固定 LP 幅值 −22.5%(含噪 −59%)崩溃,FAST 档 −0.0%(含噪 −8.5%)—— **跟踪的唯一价值是让窗跟着载波走**。
- SLOW 档在 |1−H_L(f_v)|·φ_amp > π 时失锁(vamp=6 m/s @100 kHz 误差 −45%)→ 需按动态升档。

## 散斑掉落(V3,诚实报告)

CNR=6 dB、τ_c=50 µs:gate-on 把速度尖峰中值 110 → 56 个,但位移 rms 误差 3.8 → 8.6 µm(恶化 2.3×)。掉落期间 NCO 飞轮只能外推,位移连续性无法承诺 —— 尖峰抑制以位移精度为代价。

## 档位选择规则

```python
from design_params import select_band
band = select_band(f_target_hz, v_peak)   # 'SLOW' | 'MEDIUM' | 'FAST'
```

频率优先(最低档 = 最大载波路径门限扩展),再用线性跟踪误差守卫升档:`|1−H_L(f_target)|·(2·v_peak/(λ·f_target)) ≤ 1 rad`。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py    # ~35 s, 全部断言 PASS 时退出码 0
```

断言:C1 FAST@3MHz 幅值误差 <3%;C2 FAST@3MHz SNR gain >0 dB @CNR3;C3 SLOW@100kHz SNR gain >10 dB @CNR3/40MHz;C4 三档 3MHz 幅值误差均 <5%;C5 选档逻辑;C6/C7 PLL 价值边界两面。当前结果:**7/7 PASS**(见 `results.txt`)。

## 文件

- `design_params.py` — 三档参数表、公共窗参数、选档逻辑
- `core.py` — PLL 内核与信号/工具函数(逐行移植自原项目,未改动)
- `validate_tracking.py` — V1–V4 仿真验证 + PASS/FAIL 断言
- `results.txt` — 最近一次完整运行输出
