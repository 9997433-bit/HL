# Round 8 — FEMtools 对标收官

**分支：** `cursor/round8-femtools-closure-7aa3`  
**基线：** Round 7 Wave 5 (`2d8d77d`) — 99 条 AC，八项差距功能已落地  
**目标：** 关闭 Round 7「完成定义」剩余项，形成可演示、可 CI 门禁的工业 interchange 闭环

---

## Round 7 完成定义 — 剩余项

| 项 | R8 交付 |
|----|---------|
| 端到端演示 BDF → OP2 → 相关 → 更新 → 导出 BDF | **W1** AC-WORK-010 + `examples/06_bdf_op2_industrial_loop.py` |
| `USER_GUIDE_zh.md` FEMtools 对照 + DAQ intentional gap | **W1** 文档更新 |
| 八项差距 P0/P1 AC `verified` 提升 | **W4** 批量 promotion（沿用 `promote_verified.py`） |
| Framework：`serve --desktop` 文档化 | **W1** USER_GUIDE + MS-4 工业闭环节 |

---

## 波次明细

### Wave 1 — 工业 interchange 闭环（本分支）

| 任务 | 验收 |
|------|------|
| BDF 导入 → 模态 → 合成 OP2 读回 → 相关 → 更新 → `write_bdf` | AC-WORK-010 |
| 可运行示例脚本 | `examples/06_bdf_op2_industrial_loop.py` |
| 中文指南工业闭环节 + DAQ 声明 | USER_GUIDE §11 扩展 |

### Wave 2 — Dynamics 快速重分析 CLI

| 任务 | 验收 |
|------|------|
| `openfemlab sdm scan` 刚度扫描 | AC-DYN-010 |
| Nastran driver 缺 exe 类型化失败 | AC-IO-015 |

### Wave 3 — Framework 深化

| 任务 | 验收 |
|------|------|
| `pipeline` 子命令或文档化一键脚本 | AC-WORK-011（待定） |
| OP2 corpus MSC/NX 目录约定强化 | 文档 + corpus 测试 |

### Wave 4 — 验收 promotion 与文档全绿

| 任务 | 验收 |
|------|------|
| Round 7 遗留 `implemented` → `verified` | registry CI |
| FEMtools 对照表状态列 | USER_GUIDE 全绿 |

---

## Out of scope（延续 Round 7）

- FEMtools DAQ 硬件采集
- ARTeMIS 专有接口
