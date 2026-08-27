Model slug: claude-fable-5
# Round 8 验收记录

> 状态：**探针契约就绪，功能分支并发交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `91ce6aa`（Round 7 闭合：check:round7 8/8 · check:round6 7/7）
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. 基线门禁

| # | 门禁 | 基线实测 |
|---|---|---|
| G2 | `check:round7` | 8/8 PASS |
| G3 | `check:round6` | 7/7 PASS |
| G4 | `check:round8` | **1/8（有意红灯）** |

## 1. `check:round8` 基线明细

> 运行 `npm run check:round8` 粘贴全文。

## 2. 集成回填（R8 全合入后）

### 2.1 Lighthouse Perf ≥ 95

> H6 机读：识字 98 / 100 / 100
> H6 机读：数学 99 / 100 / 100
> Lighthouse 12.8.2 · mobile / simulate；`test:acceptance` 同轮 axe 22/22 路由及 4×24 状态均为 `critical=0, serious=0`。原始报告：`evidence/r8/lighthouse-literacy-app.json`、`evidence/r8/lighthouse-math-app.json`。

| App | P | A | BP | 判定 |
|---|---:|---:|---:|---|
| 识字 | 98 | 100 | 100 | PASS |
| 数学 | 99 | 100 | 100 | PASS |

### 2.2 zip 体积

| 包 | 集成实测 |
|---|---|
| literacy-app.zip | `[待回填]` |
| math-app.zip | `[待回填]` |

## 3. 结论

`Round 8 深度门禁 [PASS/FAIL]（[N]/8）；Round 7/6 回归 [无/有] 退化。`
