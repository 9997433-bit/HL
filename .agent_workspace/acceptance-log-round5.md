# Round 5 验收记录

> 状态：**六项硬门槛全绿** — `check:round5` 8/8 PASS；探针仅剩 L-M6 字源动画待交付。
> 判定标准：`.agent_workspace/ROUND5-ACCEPTANCE.md`

记录日期：2026-08-27
集成分支：`cursor/openmoji-integration-9f67`（合并 1000 字 + 回归基线后）

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | PASS | 含识字 smoke 58 单元翻页 |
| G2 | Round 5 硬门槛 | `npm run check:round5` | **6/6** | H1–H6 全绿 |
| G3 | Round 3 全链 | `npm run test:round3` | PASS | [R5 回归门禁](bc-0e8710a4) 基线 |
| G4 | 出包 | `npm run build:all` | PASS | zip 见 §4 |
| G5 | Lighthouse | `npm run test:acceptance` | PASS | 识字/数学 96/100/100（回归分支） |

## 1. `check:round5` 六项硬门槛

| # | 检查 | 阈值 | 实测 |
| --- | --- | --- | --- |
| H1 | 字库 | ≥ 1000 | **1000** ✅ |
| H2 | 绘本 + 零越界 | ≥ 30 | **30** ✅ |
| H3 | 成语 | ≥ 60 | **60** ✅ |
| H4 | 母题 | ≥ 100 | **118** ✅ |
| H5 | 数形演示 | ≥ 7 | **8** ✅ |
| H6 | 新小游戏 | ≥ 3 | **3** ✅ |

探针：M-M5/M-M11/M-M13 教具已接线；L-M6 字源 ≥50 字仍待 [R5 成语+字源](bc-fa18a58e) 补足。

## 2. Round 3 回归

- `npm run test:round3` 退出码 0（[R5 回归门禁](bc-0e8710a4)）
- axe 20/20 路由 + 识字 42 交互态 `critical=0` / `serious=0`
- 修复：axe keep-alive 清理；庆祝层 lazy-load smoke 时序

## 3. Lighthouse（回归分支基线）

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 | 96 | 100 | 100 |
| 数学 | 96 | 100 | 100 |

## 4. 出包 zip（1000 字合并后）

| 文件 | 大小（bytes） |
| --- | ---: |
| `dist/hongen-literacy-app.zip` | 1,795,883 |
| `dist/hongen-math-app.zip` | 223,512 |

识字包增大主因：1000 字详情分片 + 500 新字 hanzi-data 笔顺离线数据。

## 5. 结论

**Round 5 内容硬门槛已闭合。** 下一步：Round 6（1800 字 / 130 绘本 / 185 母题）或并行 Round 5B Play Layer。
