Model slug: gpt-5.6-sol-xhigh-fast
# Round 8 验收记录

> 状态：**H7 报告与证据索引已交付，功能分支并发交付中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ `a8b21b3`（Round 7 闭合：
> `check:round7` 8/8 · `check:round6` 7/7）
> 报告分支：`cursor/r8-global-report-9f67`
> 判定标准：`.agent_workspace/ROUND8-ACCEPTANCE.md`

## 0. Round 8 起点基线

`a8b21b3` 新增 H1–H8 探针时，功能分支尚未合入，因此基线定义为 **1/8**：
仅 H8（Round 7 8/8 不退化）通过。该红灯是并发施工起点，不是放宽终验标准。

| 项 | `a8b21b3` 起点状态 | 收口分支 |
|---|---|---|
| H1 字源 800 | 525/800 | `r8-literacy-etymology` |
| H2 剧情/儿歌 | 58/99，u59–u99 与儿歌专题未接线 | `r8-literacy-stories` |
| H3 技能图谱 | 路由、视图、专用图谱数据未接线 | `r8-math-skillgraph` |
| H4 OCR 质量 | OCR v1 已在，固定精度基准脚本未接线 | `r8-literacy-ocr-quality` |
| H5 跟读 v2 | 跟读 v1 已在，v2 能力与 smoke 未接线 | `r8-literacy-followread` |
| H6 Perf 95 | 沿用 R7 性能结果，数学仍低于 R8 阈值；R8 原始证据目录未建 | `r8-perf-lighthouse` |
| H7 全局报告 | 仍是 Round 7 快照，尚无 R8 证据索引 | `r8-global-report` |
| H8 R7 回归 | 8/8 PASS | 全部分支共同维护 |

## 1. H7 报告分支交付

- `.agent_workspace/GLOBAL-SUMMARY-REPORT.md` 已刷新到 Round 8，保留 31/31 模块行；
  24 项达到当前口径，7 项明确标记对应 R8 功能子代理。
- `.agent_workspace/evidence/r8/README.md` 固定 Lighthouse 双 App 与 axe 三个扫描面的
  原始 JSON 路径；路径本身不冒充性能通过。
- `check:round7` 的报告状态解析兼容 R8 在途标记，避免文档进入新轮次后反向破坏
  Round 7 的 H7。
- 本分支 `check:round8` 应为 **2/8**（H7 + H8）；其余六项必须等功能分支真实合入，
  最终仍要求 8/8。

### 1.1 H7 / H8 探针输出

将在本分支终验后记录命令全文与退出码。

## 2. R8 全合入后的性能回填区

### 2.1 Lighthouse Perf ≥ 95

| App | P | A | BP | 判定 |
|---|---:|---:|---:|---|
| 识字 | `[待回填]` | `[待回填]` | `[待回填]` | |
| 数学 | `[待回填]` | `[待回填]` | `[待回填]` | |

### 2.2 zip 体积

| 包 | 集成实测 |
|---|---|
| literacy-app.zip | `[待回填]` |
| math-app.zip | `[待回填]` |

## 3. 本分支终验回归

将在提交并推送报告变更后依次执行 `npm test`、`check:round6`、`check:round7`、
`build:all`、`sync:android` 与 `check:android`，再记录可复现结果。

## 4. 结论

当前结论：H7 报告与证据索引闭合；R8 功能分支合入前总门禁保持预期红灯，
Round 7/6 必须持续无退化。
