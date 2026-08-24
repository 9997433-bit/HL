# 外差电 IQ（Polytec 类）跟踪滤波设计与验证

**架构**：RF → 下变频 → 电 IQ 复基带 `z(t)` → **纯 NCO 载波再生 PLL** → FM 鉴频。  
与零差不同：**无残差窗**；`fn` 同时决定跟踪动态与测量带宽；前端被迫随速度量程变宽。

## 档位规则（对齐 `polytec_tracking_filter_sim.m`）

```
f_acc = min(采集带宽, 100 kHz)
a_design(FAST) = 2π · f_acc · v_range
SLOW / MEDIUM / FAST = FAST / 100 / 10 / 1
fn = √(a_design / (πλ))          # e_ss = 1 rad 设计线
选档：满足 fn ≥ fn_req(v_range, f_vib) 的最窄档
fn_req = √(2·f_v·v_range / (e_crit·πλ))
```

## 运行

```bash
cd heterodyne_tracking_design
python3 validate_heterodyne.py
```

## 与零差的核心差异

| | 零差光 IQ | 外差电 IQ |
|--|-----------|-----------|
| 载波 | ~0 Hz | 随速度游走 f_D=2v/λ |
| 前端 | 可选宽 | **被迫** ~2·f_D,max |
| 测量带宽 | 公共残差窗 4 MHz | = 环路 f_3dB |
| 分档主因 | 目标振动频率 | **速度量程 + 振动频率** |
