# 1550 nm 零差 IQ 分档跟踪滤波设计与验证

基于原项目 `core.py`(`pll_carrier_regen` / 残差窗)的三档跟踪滤波方案及完整仿真验证。

## 架构(每档双路径)

- **载波路径**:PLL 载波再生(分档 fn,ζ=1.2,取环带宽经济值,见审查项 #7),纯 NCO 输出 —— 提供弱光门限扩展与掉落飞轮。
- **测量路径**:公共残差窗 —— `r = z·e^{-jφ}` 经线性相位 FIR 后重构 `y = e^{jφ}·e^{j·gs·angle(LP(r))}`。窗跟随 NCO 居中且**三档相同**:**B_win = 4 MHz 是窗的 −6 dB 截止点**,平坦(幅值误差 <1%)测量带约 **DC–3.6 MHz**(覆盖 3 MHz 规格并留余量,实测见 `validate_zeta_sweep.py` Z0)。换档不改变超声测量带宽,只改变载波环动态。

关键实测规律:点击(click)清除发生在复域残差窗内,要求 **B_loop < B_win**。ζ=1.2 下 SLOW(0.49 MHz)/MEDIUM(2.34 MHz)满足,低频 SNR 增益吃满门限扩展;FAST 档(B_loop=7.1 MHz)NCO 把部分点击跟进输出,低频增益 ~+13 dB(部分清除)—— 低频目标必须用低档(选档逻辑保证)。

**审查项 #7(ζ 的优化对象)**:原 ζ=2.65 由"NCO 路径等纹波 ±3%"推导,但最终测量输出的平坦度由公共 FIR 窗决定,与 |H_L| 无关(ζ 扫描实测:ζ∈{0.7…2.65} 全输出幅值误差极差 <0.05 个百分点)。ζ=2.65 只付出代价:B_loop=8.62·fn(vs ζ=1.2 的 4.42·fn),损失 ~2.9 dB 门限扩展余量,并把 MEDIUM 的 B_loop(4.57 MHz)推到 B_win 之上破坏 click 清除。改回 **ζ=1.2** 后:MEDIUM @100 kHz 增益 +36.2→+38.5 dB,FAST @3 MHz 增益 +2.2→**+7.9 dB**。更低 ζ(0.7/1.0)在 FAST 设计频点只再多 ~1 dB,但使 FAST 低频落在 click 清除悬崖边(种子间双峰)且欠阻尼 —— 不取。全部证据见 `validate_zeta_sweep.py` / `results_zeta_sweep.txt`。

## 系统参数

| 参数 | 值 |
|------|-----|
| 波长 | 1550 nm |
| 采样率 | 250 MS/s |
| 前端噪声带宽 | 40 MHz(双边 ENBW) |
| 环路阻尼 | ζ = 1.2(环带宽经济值;输出平坦度由窗决定,与 ζ 无关 —— 审查项 #7) |
| 残差测量窗 | 线性相位 FIR,−6 dB 截止 4 MHz,平坦区 DC–≈3.6 MHz,1025 taps @ 250 MS/s 参考设计(三档公共) |

**实现说明(审查项 #4)**:`core.residual_mode`(产品路径)与 `validate_tracking.gear_filter`(验证路径)共用同一 FIR 设计函数 `core.fir_lp_kernel`(1025 taps,Hann 窗加窗 sinc),**验证路径 = 产品路径**;原先 `residual_mode` 中未被任何验证覆盖的一阶 IIR 残差窗已弃用(`iir1_lowpass` 仅保留用于软门 gs 平滑)。两条路径的一致性由 `validate_residual_alignment.py` 断言(三档 × 100k/1M/3M 幅度误差差异 < 1%)。注意:250 MS/s 全速率单级跑 1025 taps 在硬件上不可行,实时实现需多级降采样(多相抽取 → 短 FIR → 内插)等效滤波器,且 NCO 相位路径需补 NT_WIN/2 采样群时延对齐(仿真中以 'same' 对齐等效补偿)。

## 三档设计与实测(CNR=3 dB, B_frontend=40 MHz, 12 seeds 中值)

| 档位 | 目标频段 | fn | B_loop | SNR 增益(设计频点) | 3 MHz 幅值误差(全输出) |
|------|----------|-----|--------|----------------------|--------------------------|
| SLOW | ≤ 200 kHz | 110 kHz | 0.49 MHz | **+38.5 dB** @100 kHz | +0.06% |
| MEDIUM | ≤ 1 MHz | 530 kHz | 2.34 MHz | **+18.8 dB** @1 MHz | +0.06% |
| FAST | ≤ 3 MHz | 1.60 MHz | 7.08 MHz | **+7.9 dB** @3 MHz | +0.02% |

## PLL 价值边界(V2,与固定复数低通对照)

- 静止/小摆动载波:固定 LP 与正确选档的跟踪档增益打平(+37.2 vs +37.2 dB)—— **PLL 无增值**。
- 大 Doppler 摆动(fD=7.7 MHz > B_win):固定 LP 幅值 −22.5%(含噪 −59%)崩溃,FAST 档 −0.0%(含噪 −0.6%)—— **跟踪的唯一价值是让窗跟着载波走**。
- SLOW 档在 |1−H_L(f_v)|·φ_amp > π 时失锁(vamp=6 m/s @100 kHz 误差 −35%)→ 需按动态升档。

## 散斑掉落(V3,诚实报告)

CNR=6 dB、τ_c=50 µs:gate-on 把速度尖峰中值 110 → 46 个,但位移 rms 误差 3.8 → 8.6 µm(恶化 2.3×)。掉落期间 NCO 飞轮只能外推,位移连续性无法承诺 —— 尖峰抑制以位移精度为代价。

## 档位选择规则

```python
from design_params import select_band
band = select_band(f_target_hz, v_peak)   # 'SLOW' | 'MEDIUM' | 'FAST'
```

频率优先(最低档 = 最大载波路径门限扩展),再用线性跟踪误差守卫升档:`|1−H_L(f_target)|·(2·v_peak/(λ·f_target)) ≤ 1 rad`。

## 产品 API:tracking_mode / gate_policy

产品支持 `tracking_mode ∈ {'pll','off'}`;PLL 下 `gate_policy ∈ {'auto','always'}`。**OFF 不是第四档**,是跟踪旁路:无 PLL、无残差窗,输出 `angle(z)` / FM 鉴频(即 V1/V3 对照中的 OFF 参考列);**gate-off ≠ OFF** —— `gate_policy='always'` 只旁路掉落门,PLL 仍在跟踪。

```python
from design_params import FS, cfg_for_frequency
from core import tracking_filter

cfg = cfg_for_frequency(100e3, v_peak=0.02)               # PLL + 选档, 门控 'auto'
y, phi, state, diag = tracking_filter(z, FS, cfg, Nhat)   # Nhat: 挡光标定噪声底

cfg = cfg_for_frequency(100e3, gate_policy='always')      # PLL, 门控旁路(仍在跟踪)
cfg = cfg_for_frequency(100e3, tracking_mode='off')       # 跟踪旁路: angle(z)/FM 鉴频
y, phi, state, diag = tracking_filter(z, FS, cfg)         # OFF 不需要 Nhat; state=None
```

两种模式返回同形 `(y, phi, state, diag)`;OFF 下 `y = z/|z|`(单位模,下游 `angle`/`fm_discriminator` 处理与 PLL 模式完全一致)、`state=None`(该模式不存在门控)。回归见 `validate_off_mode.py`(O1–O5:旁路路由/保真、gate-off ≠ OFF、PLL 路径逐样本一致、参数守卫)。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py              # ~35 s, 全部断言 PASS 时退出码 0
python3 validate_residual_alignment.py    # 产品路径/验证路径一致性断言
python3 validate_zeta_sweep.py            # ~50 s, ζ 扫描 + 推荐值断言(审查项 #7)
python3 validate_off_mode.py              # <5 s, OFF 模式/产品入口冒烟回归 (O1–O5)
```

断言:C1 FAST@3MHz 幅值误差 <3%;C2 FAST@3MHz SNR gain >0 dB @CNR3;C3 SLOW@100kHz SNR gain >10 dB @CNR3/40MHz;C4 三档 3MHz 幅值误差均 <5%;C5 选档逻辑;C6/C7 PLL 价值边界两面。当前结果:**7/7 PASS**(见 `results.txt`)。

`validate_residual_alignment.py` 另断言 `core.residual_mode` 与 `gear_filter` 在三档 × 100kHz/1MHz/3MHz 上的幅度误差差异 < 1%(见 `results_residual_alignment.txt`)。

`validate_zeta_sweep.py` 断言 Z3-1…Z3-6(输出幅值误差对 ζ 不敏感、MEDIUM click 清除条件、SNR 无回退、规格保持、掉光重捕、ZETA==1.2),当前 **6/6 PASS**(见 `results_zeta_sweep.txt`)。

`validate_off_mode.py` 断言 O1–O5(OFF 旁路路由与保真、gate-off ≠ OFF、`tracking_filter` 与 `residual_mode` 逐样本一致、参数守卫),当前 **5/5 PASS**(见 `results_off_mode.txt`)。

## 文件

- `design_params.py` — 三档参数表、公共窗参数、选档逻辑、产品配置入口 `cfg_for_frequency`(tracking_mode / gate_policy)
- `core.py` — PLL 内核与信号/工具函数(移植自原项目;`residual_mode` 已改为 1025-tap FIR 产品路径,见审查项 #4);产品入口 `tracking_filter` 与 OFF 旁路 `off_mode`
- `validate_tracking.py` — V1–V4 仿真验证 + PASS/FAIL 断言
- `validate_off_mode.py` — OFF 模式/产品入口冒烟回归(O1–O5,见 `results_off_mode.txt`)
- `validate_residual_alignment.py` — `core.residual_mode` vs `gear_filter` 一致性断言(审查项 #4)
- `validate_zeta_sweep.py` — ζ 扫描:幅值误差/SNR 增益/near-π 率/掉光重捕 + 推荐值断言(审查项 #7)
- `results.txt` — 最近一次完整运行输出
- `results_residual_alignment.txt` — 一致性断言最近一次运行输出
- `results_zeta_sweep.txt` — ζ 扫描最近一次运行输出
