# Round 6 验收记录

> 状态：**10 子代理并发启动中**（2026-08-27）
> 基线：`cursor/openmoji-integration-9f67` @ 90663c1
> 回归门禁：`cursor/r6-regression-gate-9f67` @ 4aae216
> 判定标准：`.agent_workspace/ROUND6-ACCEPTANCE.md`

## 基线门禁

| # | 门禁 | 命令 | 基线 |
|---|---|---|---|
| G1 | 全量单测 | `npm test` | PASS（exit 0） |
| G2 | Round 5 不退化 | `npm run check:round5` | PASS · 12/12 |
| G3 | Round 5B 不退化 | `npm run check:round5b` | PASS · 6/6 |
| G4 | Round 6 | `npm run check:round6` | **FAIL · 1/7**（exit 1，预期红灯） |
| G5 | Round 3 全链 | `npm run test:round3` | 沿用基线 PASS（本轮未复跑） |

### Round 6 红灯明细（1/7）

- ✅ H2 `verifyBookCoverage` 零越界。
- ❌ H1 字库 **1000/1800** 字。
- ❌ H2 绘本 **30/130** 本。
- ❌ H3 古诗未接线（要求 ≥ 20 首）。
- ❌ H4 跟读评测：路由缺失、识别/录音降级 pipeline 缺失；条件式 smoke stub 已就位。
- ❌ H5 识字小游戏 **3/5** 款（不含 listen）。
- ❌ H6 应用题母题 **118/185** 个。

### 2026-08-27 回归执行摘要

- `npm run check:round6`：exit 1；`1/7` 通过、6 项失败，均为上述内容分支待交付项。
- `npm run check:round5`：exit 0；12 项通过、0 pending、0 失败。
- `npm run check:round5b`：exit 0；6 项通过、0 失败。
- `npm test`：exit 0；共用反馈、识字数据/构建/浏览器 smoke、数学内容/构建/浏览器
  smoke 全部通过。

## 结论

Round 5 / 5B 与全量测试无回归；Round 6 保持预期红灯，待内容子代理合入后复跑转绿。
