# 外差电IQ(Polytec类)跟踪滤波设计与验证

基于原项目 `core.py`(`pll_carrier_regen` 纯 NCO)的外差三档跟踪滤波方案及完整仿真验证。默认 HeNe 632.8 nm(与 `polytec_tracking_filter_sim.m` 一致),所有函数支持显式传 `lam=1550e-9`。

## 架构(与零差方案的哲学差异)

- **纯 NCO 架构**(OFV-3001 附录 D.2:跟踪滤波器输出 = 再生载波,解码在下游):`y = e^{jφ_NCO}`,**没有零差那样的残差测量窗**。
- 因此**档位是单旋钮**,同时决定:
  - **测量带宽** `f_3dB = 2.058·fn`(渐近 −20 dB/dec,高于 f_3dB 的谱线只能用已知 |H_L| 做频响校正,校正恢复幅值刻度但不改变谱线 SNR);
  - **跟踪动态** `a_design = π·λ·fn²`(e_crit=1 设计线),`a_slip ≈ π·a_design`(e_crit=π 卷绕线)。

## 系统参数(四层带宽,禁止 fs == 噪声带宽)

| 参数 | 值 | 角色 |
|------|-----|------|
| λ | 632.8 nm(默认)| HeNe,可传 1550 nm |
| fs | 50 MS/s | 只决定混叠:v_alias = λ·fs/4 = 7.91 m/s(H1 数值证实非噪声带宽)|
| B_frontend | 19 MHz | 复基带双边 ENBW,决定 CNR 与噪声功率 |
| f_dev_max | 9.5 MHz | IF 频偏硬边缘:v_if = λ·f_dev/2 = 3.01 m/s(与 ENBW 是两个参数)|
| ζ | 0.707 | B_loop = 3.332·fn(单边 ENBW)|

## 三档 fn 推导([自研]规则,对齐 polytec sim 的 `mode_params`)

1. `a_design(FAST) = 2π·f_acc·v_range`,`f_acc = min(采集带宽 1 MHz, cap 100 kHz)`;
2. MEDIUM = FAST/10,SLOW = FAST/100(a_design 比例)→ fn 每档 /√10;
3. `fn = sqrt(a_design/(π·λ))`(e_crit=1 设计线)。

v_range = 1 m/s 演示档(H1/H2 用):

| 档 | fn | f_3dB(=测量带宽) | B_loop | a_design / a_slip | 浴缸谷底(e=π) | 底噪改善 vs OFF |
|----|-----|------|--------|--------------------|----------------|----------------|
| SLOW | 56.2 kHz | 116 kHz | 187 kHz | 6.3e3 / 2.0e4 m/s² | 79 mm/s @ fn | +17.1 dB |
| MEDIUM | 177.8 kHz | 366 kHz | 592 kHz | 6.3e4 / 2.0e5 | 250 mm/s | +12.1 dB |
| FAST | 562.2 kHz | 1157 kHz | 1873 kHz | 6.3e5 / 2.0e6 | 790 mm/s | +7.1 dB |

离散守卫 `fn ≤ fs/50`:v_range ≤ 3 m/s 全过;10 m/s 的 FAST(1.78 MHz)触发 —— 实机需提高 fs 或降 f_acc_cap(C01)。

## 仿真验证摘要(H1–H6,21/21 PASS,见 `results.txt`)

- **H1 四层带宽敏感性**:环内 σφ² 与理论 `s2·B_loop/B_frontend` 吻合 ±0.4 dB;fs 50→100 MHz 时 σφ² 变化 −0.05 dB(**fs 不是噪声带宽,数值证实**);B_frontend 减半 → 方差 ×1.84;三档方差比 ×3.18 / ×3.05 ≈ √10。
- **H2 三档弱光 CNR sweep**(R1–R4 公平规则,gate='always' 隔离门):SLOW@50 kHz 谱线 SNR 增益 CNR=0 时 **+40.0 dB**、CNR=4 **+35.3 dB**、CNR=20 仅 +0.4 dB —— **增益本质是 FM 门限扩展,只在门限以下存在**。FAST@5 MHz:未校正底噪下降 +15.3 dB(复现用户 PSV-500 弱回光实测),但谱线 SNR 增益 +0.2 dB ≈ 0(底噪下降与信号衰减同源于 |H_L|);未校正幅值 ×5.8 衰减(复现"10 MHz FAST 衰减数倍"),精确离散 H_L 校正后 −1.6%。SLOW@5 MHz 幅值比 0.016 —— **档位=测量带宽,无残差窗兜底**。
- **H3 量程扫描 fn 参数化 vs 固定 fn=400k(旧硬编码)**:3 m/s 时固定档失锁(err −94.9%,374 周跳),参数化 −0.0%、0 周跳;10 mm/s 时参数化噪声增益高 +17.5 dB。旧的固定 fn 自相矛盾问题被数值坐实。
- **H4 浴缸形动态边界**(MEDIUM 档,纯 PLL):5 个频点(fn/8…8fn)实测边界全部夹在理论卷绕线 `v_π(f) = π·λ·f/2/|1−H_L|` 的 [0.5, 2]× 内;谷底实测在 f=fn(177 mm/s,理论 250 mm/s = π·λ·fn/√2);OFF 鉴频器同点 err +0.02% —— **浴缸边界是跟踪环自身的代价,不是画出来的**。整机包络 = min(PLL 边界, v_if=3.01, v_alias=7.91)。
- **H5 e_crit=1 vs π**(t5/o5 复现):e=1 全量程 |err| ≤ 5.6%,PLL 谱线增益 +7.8…+25.3 dB;e=π 全量程 err −45…−96% —— **在卷绕线上设计保证失败**。
- **H6 固定 preLP 同 B_loop 对照**:前端被量程强制到 2·f_D 宽,preLP 在 v ≥ 0.2 m/s 幅值 −97…−100% 崩溃,PLL 保持 |err| < 1.5% —— **外差大频偏场景下跟踪滤波的唯一结构性价值**(零差场景固定 LP 反而够用,见 homodyne V2)。

## 原先推测 → 现已数值证实

1. 浴缸谷底精确在 f=fn、谷值 π·λ·fn/√2(.m 中解析推导)→ H4 闭环夹逼证实(C41/C42)。
2. fs 只决定混叠、不是噪声带宽(noise_bandwidths.m 教义)→ H1 C12 直接实测。
3. 弱光增益 = FM 门限扩展,高 CNR 归零 → H2 C21/C22。
4. 用户 PSV-500 两条实测(5 MHz 弱回光底噪下降;高频 FAST 幅值衰减数倍)均由 |H_L| 滚降 + 门限机制定量复现 → H2 C23/C24。
5. 固定 fn=400k 硬编码自相矛盾(polytec sim 头注释指出)→ H3 C32/C33 数值坐实必须按量程参数化。
6. e_crit=1 可用 / e_crit=π 必败、固定 preLP 在外差大频偏下崩溃(t5/o5)→ H5/H6 以本三档规则复核。

## 运行

```bash
cd heterodyne_tracking_design
python3 validate_heterodyne.py    # ~6 s, 全部断言 PASS 时退出码 0
```

## 文件

- `design_params.py` — 三档 fn 推导([自研]规则)、四层带宽、浴缸边界、选档逻辑
- `core.py` — PLL 内核与信号/工具函数(逐行移植自原项目 `04_Python独立验证/core.py`,未改动)
- `validate_heterodyne.py` — H1–H6 仿真验证 + 21 条 PASS/FAIL 断言
- `results.txt` — 最近一次完整运行输出
