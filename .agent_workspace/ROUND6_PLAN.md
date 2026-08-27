# Round 6 — 超越 FEMtools 落后项

**Branch:** `cursor/round6-femtools-surpass-7aa3`  
**Goal:** 在 Round 5 parity 基础上，关闭仍落后于 FEMtools 的硬差距。

## 落后项 → 超越策略

| FEMtools 优势 | Round 6 目标 | 优先级 |
|---|---|---|
| SSI/OMA 输出-only 辨识 | `ssi_cov` 数值核 + 稳定图 + AC-MPE-007 | P0 |
| OP2 工业互操作 | 导出 `read_op2*`、`OPENFEMLAB_OP2_CORPUS`、Phase 4 CORD | P0 |
| 概率/UQ | `openfemlab.uq` Monte Carlo + DOE + AC-UQ-001 | P1 |
| GUI | Dashboard 增强 + `openfemlab serve` 桌面化文档 | P1 |
| 元素库深度 | Timoshenko/偏移/更多 OP2 卡片 | P2 |
| 百万 DOF 规模 | Rust/PyO3 装配核（远期） | P3 |

## 本轮交付（进行中）

| 任务 | 状态 |
|---|---|
| SSI-COV 实现 | in progress |
| OP2 导出 + corpus 框架 | in progress |
| UQ Monte Carlo 模块 | in progress |
| AC registry 66 → 68 | pending |
| 文档 MODULE_SPEC / ACCEPTANCE_CRITERIA | pending |

## 验证

```bash
python3 -m ruff check src tests
python3 -m pytest
python scripts/bench_ci_gate.py
```
