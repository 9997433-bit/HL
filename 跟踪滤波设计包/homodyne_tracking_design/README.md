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

V3 的档位由 `select_band(3 MHz, 20 mm/s)` 给出 —— 守卫先行规则下为 **SLOW**(见"档位选择规则")。CNR=6 dB、τ_c=50 µs、12 种子中值:gate-on 把速度尖峰中值 110 → 17 个,位移 rms 误差 3.8 → 0.9 µm(**改善 4.3×**)—— 本组实测尖峰抑制未付出位移精度代价(V3 结论行按实测 dr_on/dr_off 动态生成,不再静态断言"以位移精度换取")。但掉落期间 NCO 飞轮只能外推,位移连续性仍无法承诺。

## 档位选择规则(守卫先行)

```python
from design_params import select_band
band = select_band(f_target_hz, v_peak)   # 'SLOW' | 'MEDIUM' | 'FAST'
```

在通过线性跟踪误差守卫 `|1−H_L(f_target)|·(2·v_peak/(λ·f_target)) ≤ 1 rad` 的档位中选**最窄档**(最低 B_loop = 最大弱光门限扩展);全不通过取 FAST。测量带宽由公共 4 MHz 残差窗决定、与档位无关,所以高频小振幅也用低档:`select_band(3e6, 0.02)` = **SLOW**(φ_err ≈ 0.009 rad,远低于守卫;V1 实测 3 MHz 下 SLOW 增益 +9.3 dB 还优于 FAST 的 +7.9 dB)。仅当 `v_peak=None`(无法评估守卫)时退化为频段规则(≤200 kHz → SLOW;≤1 MHz → MEDIUM;其余 FAST)。

带迟滞的 `select_band_hysteresis` 同样守卫先行:升档立即生效,降档每次更新只降一档(防抖);频率-only 的 rise 阈值(200 kHz / 1 MHz)已废除 —— 它与守卫先行规则矛盾(审计:3 MHz/20 mm/s 必须得 SLOW 而非 FAST)。因此 `cfg_for_frequency(3e6, v_peak=0.02)`(默认带迟滞)与 `select_band_hysteresis(3e6, 'SLOW', 0.02)` 都返回 **SLOW**,与 `select_band` 一致。

**降级区标志(审计项 2,选项 A)**:PLL cfg dict 额外携带 `phi_err / guard_ok / overrange`(`design_params.guard_flags`;`v_peak=None` 时三者为 `None`)。用户全域(f ≤ 100 kHz, v ≤ 30 m/s)内唯一超守卫组合是 66–100 kHz × 高速:`cfg_for_frequency(100e3, 30.0)` 返回 `guard_ok=False, overrange=True, phi_err=1.50 rad`(< π,仍可跟踪,`validate_app_30ms_100khz.py` A2/A8 实测 clean 误差 ~0、含噪真滑周 p95=1 每 0.5 ms)——产品应把 `overrange` 上报给用户。保持 FAST fn=1.6 MHz:提高到 2.1–2.2 MHz 可过守卫但在 3 MHz 规格点损失 2.7–3.3 dB 弱光 SNR,实测对比见 `study_fast_fn_options.py`。

## 产品 API:tracking_mode / gate_policy

产品支持 `tracking_mode ∈ {'pll','off','fixed_lp'}`;PLL 下 `gate_policy ∈ {'auto','always'}`。**OFF 不是第四档**,是跟踪旁路:无 PLL、无残差窗,输出 `angle(z)` / FM 鉴频(即 V1/V3 对照中的 OFF 参考列);**gate-off ≠ OFF** —— `gate_policy='always'` 只旁路掉落门,PLL 仍在跟踪。`fixed_lp` 是固定测量窗模式:无 PLL,仅对 z 施加公共 B_WIN 复低通(V2 LP-Bwin 参考路径)—— 跟踪关闭但保留固定窗噪声底,不是 raw `angle(z)`。

```python
from design_params import FS, cfg_for_frequency
from core import tracking_filter

cfg = cfg_for_frequency(100e3, v_peak=0.02)               # PLL + 选档, 门控 'auto'
y, phi, state, diag = tracking_filter(z, FS, cfg, Nhat)   # Nhat: 挡光标定噪声底

cfg = cfg_for_frequency(100e3, gate_policy='always')      # PLL, 门控旁路(仍在跟踪)
cfg = cfg_for_frequency(100e3, tracking_mode='off')       # 跟踪旁路: angle(z)/FM 鉴频
y, phi, state, diag = tracking_filter(z, FS, cfg)         # OFF 不需要 Nhat; state=None

cfg = cfg_for_frequency(100e3, tracking_mode='fixed_lp')  # 固定窗: y = LP_Bwin(z), 无 PLL
y, phi, state, diag = tracking_filter(z, FS, cfg)         # 同样不需要 Nhat; state=None
```

三种模式返回同形 `(y, phi, state, diag)`;OFF 下 `y = z/|z|`(单位模,下游 `angle`/`fm_discriminator` 处理与 PLL 模式完全一致)、`state=None`(该模式不存在门控);`fixed_lp` 下 `y = LP_Bwin(z)`(保留窗幅度响应,与 `fir_lp_same` 参考逐样本一致)、`phi = angle(y)`、`state=None`。回归见 `validate_off_mode.py`(O1–O6:旁路路由/保真、gate-off ≠ OFF、PLL 路径逐样本一致、参数守卫、fixed_lp 路由与 fixed_lp ≠ OFF)。

## 运行验证

```bash
cd homodyne_tracking_design
python3 validate_tracking.py              # ~35 s, 全部断言 PASS 时退出码 0
python3 validate_residual_alignment.py    # 产品路径/验证路径一致性断言
python3 validate_zeta_sweep.py            # ~50 s, ζ 扫描 + 推荐值断言(审查项 #7)
python3 validate_off_mode.py              # <5 s, OFF/fixed_lp 模式冒烟回归 (O1–O6)
python3 validate_app_30ms_100khz.py       # ~30 s, 用户场景 A1–A8(30 m/s / 100 kHz,含审计项 1–4)
python3 study_fast_fn_options.py          # ~7 s, 审计项 2 fn 选项对比研究(FN1–FN3)
```

断言:C1 FAST@3MHz 幅值误差 <3%;C2 FAST@3MHz SNR gain >0 dB @CNR3;C3 SLOW@100kHz SNR gain >10 dB @CNR3/40MHz;C4 三档 3MHz 幅值误差均 <5%;C5 选档逻辑;C6/C7 PLL 价值边界两面。当前结果:**7/7 PASS**(见 `results.txt`)。

`validate_residual_alignment.py` 另断言 `core.residual_mode` 与 `gear_filter` 在三档 × 100kHz/1MHz/3MHz 上的幅度误差差异 < 1%(见 `results_residual_alignment.txt`)。

`validate_zeta_sweep.py` 断言 Z3-1…Z3-6(输出幅值误差对 ζ 不敏感、MEDIUM click 清除条件、SNR 无回退、规格保持、掉光重捕、ZETA==1.2),当前 **6/6 PASS**(见 `results_zeta_sweep.txt`)。

`validate_off_mode.py` 断言 O1–O6(OFF 旁路路由与保真、gate-off ≠ OFF、`tracking_filter` 与 `residual_mode` 逐样本一致、参数守卫、O6a fixed_lp 路由 == `fir_lp_same` 参考、O6b fixed_lp ≠ OFF),当前 **7/7 PASS**(见 `results_off_mode.txt`)。

`validate_app_30ms_100khz.py` 断言 S1/S2、E1–E5、G1、H1–H3、F1–F3(审计项 1:前端模型一致性)、D1–D3(审计项 3:掉光重捕获)、N1/N2(审计项 4:含噪滑周分位数),当前 **19/19 PASS**(见 `results_app_30ms_100khz.txt`);五项审计意见的必要性判定汇总见 `审计必要性评估.md`。

## 工程提醒(审计项 5)

- `validate_ellipse_switching.py` 中的 `SwitchingStateMachine`(S2/S3 换面重捕状态机)是**验证原型**,未经产品化评审(无实时约束、无资源/定点化分析),不得直接搬入产品代码;产品实现须另行评审后按其行为规格重写。
- `cfg_for_frequency` 的位置参数顺序为 `(f_target_hz, v_peak, current_band)`(与 `select_band` 对齐)。已全仓 grep 确认现有调用点(`validate_app_30ms_100khz.py`、`validate_off_mode.py`、README 示例)均为正确顺序或关键字传参;新代码建议对 `current_band` 及其后的参数一律用关键字传参。

## 文件

- `design_params.py` — 三档参数表、公共窗参数、守卫先行选档逻辑(含迟滞)、守卫标志 `guard_flags`(phi_err/guard_ok/overrange)、产品配置入口 `cfg_for_frequency`(tracking_mode pll/off/fixed_lp,gate_policy)
- `core.py` — PLL 内核与信号/工具函数(移植自原项目;`residual_mode` 已改为 1025-tap FIR 产品路径,见审查项 #4);产品入口 `tracking_filter` 与 OFF 旁路 `off_mode` / 固定窗 `fixed_lp_mode`
- `validate_tracking.py` — V1–V4 仿真验证 + PASS/FAIL 断言
- `validate_off_mode.py` — OFF / fixed_lp 模式与产品入口冒烟回归(O1–O6,见 `results_off_mode.txt`)
- `validate_residual_alignment.py` — `core.residual_mode` vs `gear_filter` 一致性断言(审查项 #4)
- `validate_zeta_sweep.py` — ζ 扫描:幅值误差/SNR 增益/near-π 率/掉光重捕 + 推荐值断言(审查项 #7)
- `validate_app_30ms_100khz.py` — 用户场景验证 A1–A8(v ≤ 30 m/s、典型 f ≤ 100 kHz;含审计项 1/3/4 的 A6 前端一致性、A7 掉光重捕获、A8 含噪滑周统计,见 `results_app_30ms_100khz.txt`)
- `study_fast_fn_options.py` — 审计项 2:FAST fn 选项(1.6M vs 2.0/2.1/2.2M)实测对比与选项 A 决策依据(见 `results_fast_fn_options.txt`)
- `审计必要性评估.md` — 五项审计意见的必要性判定(必要/可选/不必)与关键实测数字
- `results.txt` — 最近一次完整运行输出
- `results_residual_alignment.txt` — 一致性断言最近一次运行输出
- `results_zeta_sweep.txt` — ζ 扫描最近一次运行输出
