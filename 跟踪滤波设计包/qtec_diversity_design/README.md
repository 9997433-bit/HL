# QTec 多路散斑分集 (P0 + P1)

Polytec **QTec®** 类多通道散斑分集接收的 Python 仿真:多路独立解调 + SNR 加权非相干合成,把散斑掉光概率从单路的 p 压到 ~p^M。本目录是"四类研究"中的第 4 类,P0(多路散斑基础设施)与 P1(速度域非相干合成 baseline)已实现并通过断言验证。

## 原理(为什么多打几个探测器就能救掉光)

单探测器 LDV 的致命弱点:粗糙表面回光是散斑场,单路复包络 h(t) 服从 Rayleigh 统计,强度低于均值 F 倍的概率 p = 1 − e^(−F)(−9.8 dB 深衰落时 p ≈ 10%)。掉进深衰落 → CNR 崩溃 → FM 鉴频出 click 尖峰、PLL 失锁。

QTec 的解法:用 M 个**空间分离**的接收孔径(或光斑内不同空间模式),各自看到**近独立**的散斑实现。所有通道同时掉进深衰落的概率是 p^M —— M=4 时 10% 变成 0.01%。每路独立解调后按每路瞬时 SNR 加权合成,输出始终"跟着亮的通道走"。

本包实现 **Dräbenstedt 路线**(务实的 P1 baseline):每路独立 PLL 载波再生 + FM 鉴频,**速度域**块式 SNR 加权非相干合成 —— 不需要跨通道相位对齐(散斑相位 ψ_k 各不相同且随时间漂移,速度 = 相位导数,静态偏移天然消掉)。

## 与 homodyne / heterodyne 的关系

- **每路解调器 100% 复用** `homodyne_tracking_design`:`core.pll_carrier_regen`(载波路径)+ 公共 4 MHz 残差窗(等价 `validate_tracking.gear_filter` 全输出路径),常量 FS/LAMBDA/档位/门参数 import 自 `design_params` —— 无 fork,单一事实源;homodyne 目录未被修改(PEP 420 命名空间包 import,无 circular import)。
- C_k(每路载波功率)PLL 内部不外露,由 `diversity_combine.estimate_C` **wrapper 重算**:与环内相同的 tauP 一阶 IIR 滤 |z|²,减 Nhat 截零。
- 外差(`heterodyne_tracking_design`)体制同样适用分集合成 —— 把每路解调器换成外差 NCO 链即可,列入 P4 路线图。

## P0 范围(多路散斑基础设施)

- `speckle_multi.py` — `make_speckle_multi(N, fs, tau_c, M, rho, rng)`:M 路带限 Rayleigh 散斑,rho 为两两**场**相关(公共分量混合法,强度相关 = rho²);`fade_prob_theory` / `joint_fade_fraction` / `channel_correlation` 联合深衰落统计工具。
- `synth_multichannel.py` — `z_k = h_k·exp(j(φ+ψ_k)) + n_k` 多路 IQ 合成,每路独立前端噪声,平均每路 CNR 可配。
- **验证(Q0-1…Q0-5 全 PASS)**:单路衰落率与 Rayleigh 理论差 <0.2%;M=3/4 联合衰落率 = 独立外推 p^M 的 1.00×/1.01×(−4.5 dB 门限,30 万 τ_c/通道);−9.8 dB 深衰落 M=3 为 0.95×;rho=0.5 时实测场相关 0.499 且联合衰落率升到独立外推的 1.59× —— 通道相关会侵蚀分集增益,P1 用 rho=0 做上限 baseline。

## P1 范围(非相干 SNR 加权合成 baseline)

`diversity_combine.py`:

- 每路 `channel_demod` = `pll_carrier_regen` + 可选残差窗(`use_residual`)+ FM 鉴频;
- 块式权重(块长默认 2 µs):`q_k = (C_k/Nhat_k)^α · LOCK_k · gs_k`,归一化 Σw=1;
- **跨通道相对门**:`q_k < rel_x·max(q)` 清零(默认 rel_x=0.05);
- **全暗 HOLD 飞轮**:所有 q=0 的块保持上一块权重(各路 NCO 同时在环内飞轮);
- α ∈ {1, 2, ∞}:α=1 为速度域 MRC(平稳噪声方差最优),α=∞ 纯选路,**α=2 为推荐默认**(尖峰抑制优于 α=1,静默段 SNR 增益比 α=1 低 ~0.8 dB;α=∞ 尖峰最少但平均增益只剩 +0.69 dB)。

**实测(M=3,每路 CNR=6 dB,τ_c=50 µs,SLOW 档 —— `select_band(3 MHz, 20 mm/s)` 守卫先行选出,3 MHz burst,10 seeds 中值,对照为每 seed 每指标的最优单路 oracle;见 `results_diversity.txt`)**:

| 指标 | 最优单路 (oracle) | 合成 α=1 | 合成 α=2 (默认) | 合成 α=∞ |
|------|------|------|------|------|
| 速度尖峰 (>0.4 m/s) | 10.5 | 5.5 | **5.0** | 4.0 |
| 静默段 SNR 增益 | 0 dB (基准) | +3.54 dB | **+2.75 dB** | +0.69 dB |
| 全暗 HOLD / 失锁时间 | 17.5%(失锁) | 6.40% | **6.40%** | 6.40% |
| 幅值偏置 (R1 近无噪+散斑) | — | +0.88% | **+1.25%** | +1.44% |

注:早期版本曾在 FAST 档下测得 α=2 静默段增益 +4.93 dB —— 那是选档规则修正(守卫先行,3 MHz/20 mm/s → SLOW)之前的错误档位;当前 SLOW 档实测为 **+2.75 dB**(断言 Q1-2 阈值 >+2 dB)。

诚实说明:速度域非相干合成**不改变单路 FM 门限本身**,它买到的是联合掉光率 ~p^M、静默段噪声加权平均下降、尖峰只在全通道同弱时出现。更低 CNR 下的门限扩展需要 IQ 域相干合成(P2)。

## 运行验证

```bash
cd qtec_diversity_design
python3 validate_diversity_p0_p1.py    # ~15 s;全部断言 PASS 时退出码 0
```

结果 tee 到 `results_diversity.txt`(本目录);设环境变量 `QTEC_ARTIFACTS_DIR` 可额外复制一份到指定目录(默认尝试 `/opt/cursor/artifacts`,失败静默忽略)。当前 **10/10 PASS**(Q0-1…Q0-5,Q1-1…Q1-5)。

## 路线图

- **P2 相干合成**:估计每路静态相位 ψ_k 与慢变散斑相位,IQ 域复数 MRC(Σ ŵ_k* z_k)后再进单个 PLL/鉴频 —— 合成发生在鉴频**之前**,可获得真正的 FM 门限扩展(比速度域合成多 ~10·log10(M) dB 的门限余量),代价是相位对齐环路。
- **P3 位移连续性与自适应**:掉落桥接(用合成权重置信度驱动位移域外推/卡尔曼融合,替代目前"HOLD 飞轮只保速度"),权重平滑内插取代块式 ZOH,块长/rel_x 随 τ_c 自适应,K>0(镜面+漫射)散斑。
- **P4 工程化**:多通道 AFE/FPGA 多相实现与资源评估(M 路 PLL + 公共残差窗的复用调度)、在线 Nhat 标定、相关散斑(rho>0,孔径间距不足)下的增益退化标定、外差体制(heterodyne core)复用验证。

## 文件

- `_pkgpath.py` — sys.path 引导(import 兄弟目录 homodyne 包,不改动其内容)
- `speckle_multi.py` — M 路散斑生成 + 联合深衰落统计(P0)
- `synth_multichannel.py` — 多路 IQ 观测合成(P0)
- `diversity_combine.py` — 每路解调 + 块式 SNR 加权合成(P1)
- `validate_diversity_p0_p1.py` — P0+P1 断言验证(退出码非 0 = FAIL)
- `results_diversity.txt` — 最近一次完整运行输出
