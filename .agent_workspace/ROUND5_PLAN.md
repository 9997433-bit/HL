# Round 5 — SOTA parity

**Branch:** `cursor/round5-sota-parity-7aa3`  
**Goal:** LOBPCG、OP2 几何、参数解析器、Web 3D、CI 基准门禁、SSI API 接缝。

| 任务 | 状态 | 说明 |
|------|------|------|
| LOBPCG (`sparse_method="lobpcg"`) | done | `ModalSolver` + AC-PERF-004 |
| OP2 Phase 3 `read_op2` | done | GEOM1/GEOM2 + EPT/MPT；AC-IO-004 |
| 参数解析器 | done | `updating.resolver` + AC-UPD-010 |
| Web 3D 后处理 | done | `dashboard` three.js + 2D 回退 |
| HTML 报告 MAC 热力图 | done | `report/html.py` |
| CI 基准门禁 | done | `scripts/bench_ci_gate.py` + AC-PERF-005 |
| SSI-COV API | done | `mpe.ssi_cov` stub + AC-MPE-006 |
| Registry | done | 61 → 66 条 AC |

## 验证

- `python3 -m ruff check .`
- `python3 -m pytest`
- `python scripts/bench_ci_gate.py`

## 诚实边界

- OP2 仍无真实 Nastran corpus；`read_op2` 未导出到 `openfemlab.io`
- SSI-COV 数值核未实现
- Rust 装配核仍为远期项
