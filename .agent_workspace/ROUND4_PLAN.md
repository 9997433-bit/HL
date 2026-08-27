# Round 4 — Performance 下沉 & SOTA 收敛

**Branch:** `cursor/perf-round4-accel-7aa3`  
**Goal:** 在保持 Python 平台层的前提下，把 L2/L3 热路径加速到工业可用规模，并在开源维度上超越 FEMtools 的自动化/可复现性。

## Round 4 交付（本轮）

| 任务 | 状态 | 说明 |
|------|------|------|
| R4-T01 Numba MAC | done | `openfemlab.accel`, AC-PERF-003 |
| R4-T02 修正重分析 | done | `ScalingModel` 仿射快装配 + ModalSolver 实例复用 |
| R4-T03 bench CLI | done | `openfemlab bench modal` |
| R4-T04 文档 | done | `docs/PERFORMANCE.md` |

## 相对 FEMtools 的「已超越」维度

- **CI 验收：** 61 条 AC（含 PERF-003），机器可读 registry
- **零文件上手 + 中文向导 + Web 后处理**
- **开源 + MIT + solver-independent**
- **50k DOF 稀疏模态**（AC-PERF-001）+ **大 MAC 加速**（AC-PERF-003）

## 尚未超越（诚实边界）

- 30 年 GUI 桌面壳、全求解器适配目录
- 百万 DOF 非线性 FE（需 C++/Fortran 核）
- SSI/OMA、完整 OP2 几何、CMS 等 Round 3 deferral

## 下一阶段（Round 5 候选）

1. Rust/PyO3 装配热路径（`core/assembly` triplet fill）
2. LOBPCG + 预条件（GAP-13 剩余）
3. 修正循环 modal cache（同 θ 邻域跳过完整 eigensolve）
4. Desktop Electron/Tauri 壳（可选）
