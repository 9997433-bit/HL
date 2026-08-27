# Round 7 — FEMtools 全功能对标计划（八项）

**主分支：** `cursor/round7-femtools-full-7aa3`  
**基线：** Round 6 (`576e3ef`) — 72 条 AC，核心模态/相关/更新/MPE 已齐  
**目标：** 按用户确认的 8 个差距维度，分波次交付可验收增量，直至 FEMtools 产品线功能对标（不含 DAQ 硬件采集，明确 out-of-scope）

---

## 八项差距 → 波次映射

| # | 差距维度 | FEMtools 参照 | OpenFEMLab 交付 | 波次 |
|---|----------|---------------|-----------------|------|
| **1** | Dynamics（SDM/MBA/FBA） | FEMtools Dynamics | `solver.sdm` SDM → MBA → FBA | W1–W3 |
| **2** | Framework（驱动 + 桌面） | Framework + 外部求解器 | `io.drivers.nastran`、BDF 导出、`serve --desktop` | W1–W4 |
| **3** | Pretest 全套件 | Pretest 模块 | 质量加载、激振器 MKE、试验模型导出 | W1–W3 |
| **4** | Correlation 全套件 | Correlation 模块 | SAC/CSAC/CSF、CORTHOG、双根配对 | W1–W2 |
| **5** | Updating 工业扩展 | Model Updating | 谐波力识别、MMU、超单元、deck 导出 | W2–W4 |
| **6** | 选配（RBPE 等） | RBPE、ARTeMIS | `mpe.rbpe`；DAQ **不做** | W1–W2 |
| **7** | 规模与格式 | 无规模限制、全格式 | Rust 主装配、OP2/BDF 深覆盖 | W1–W4（延续 Round 6） |
| **8** | 可视化 | 专用查看器 | `viz` 并排/叠加、dashboard 动画 | W1–W3 |

---

## 波次明细

### Wave 1（本分支）— 地基 + 可测 MVP

| 任务 | 模块 | 验收 |
|------|------|------|
| SAC / CSAC / CSF | `solver.dynamics` + `correlation.frf` | AC-CORR-010 |
| CORTHOG | `correlation.mac` | AC-CORR-011 |
| SDM 模态域修改 | `solver.sdm` | AC-DYN-006 |
| `write_bdf` + Nastran runner stub | `io.nastran` / `io.drivers` | AC-IO-008 |
| 加速度计质量加载 | `pretest.mass_loading` | AC-PRETEST-006 |
| RBPE（模型总质量/CG） | `mpe.rbpe` | AC-MPE-008 |
| 并排振型动画 | `viz.plotting` | AC-WORK-006（contract） |
| MBA/FBA 规格 + stub | `solver.mba` | spec only，W2 实现 |

### Wave 2 — Dynamics 产品化

- MBA：两部件模态模型耦合（连接 DOF 刚度）
- FBA：两部件 FRF 在连接处装配（阻抗元件）
- 快速重分析 API（参数扫描，无 GUI 滑块先 CLI）
- 调谐吸振器单元（弹簧-质量-阻尼修改元）

### Wave 3 — Pretest + Correlation 深化

- 激振器/悬挂点动能排序
- MAC 剔除测点、迭代 Guyan 预试验
- 试验模型导出（UFF + Euler 角 meta）
- 双根模自动配对启发式
- 几何对齐 CLI（刚性变换 + 最近点映射）

### Wave 4 — Updating + Framework

- 谐波力识别（ODS → 等效谐波载荷）
- MMU（多模型联合残差）
- `write_bdf` 携带更新后材料/刚度缩放
- Ansys/Abaqus 驱动 stub（环境变量 + 文档）
- Dashboard：FRF 叠加、稳定图交互

### Wave 5 — 规模与格式收官

- Rust 装配接入 `core.assembly` 主路径（AC-PERF-006）
- OP2 CBAR/BAR 完整 parity
- 真实 MSC/NX corpus 门禁（opt-in）

### Out of scope（文档声明）

- **FEMtools DAQ** 硬件采集
- **ARTeMIS 专有接口**（UFF 交换替代）

---

## 代理执行规则

1. 每波独立分支 `cursor/round7-<wave>-7aa3` 或延续 `round7-femtools-full-7aa3` 至 W1 合并前。
2. 每波：spec → 实现 → AC/registry → pytest + ruff → commit → push → PR。
3. `specified` 行必须先有 `@criterion` 测试再标 `implemented`。
4. 波次间依赖：W2 依赖 W1 SDM；W4 MMU 依赖 W2 MBA。

---

## 完成定义（FEMtools 全对标）

- [ ] 八项表格中每行至少有一个 P0/P1 AC `verified`
- [ ] `docs/USER_GUIDE_zh.md` FEMtools 对照表全绿
- [ ] DAQ 在文档中标记为 intentional gap
- [ ] 端到端演示：BDF → Nastran(可选) → OP2 → 相关 → 更新 → 导出 BDF
