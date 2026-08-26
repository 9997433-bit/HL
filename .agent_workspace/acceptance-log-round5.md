# Round 5 验收记录（部分回填）

> 状态：**进行中** — Round 3 回归 PASS；六项硬门槛 **5/6 已绿**，仅 H1 字库待 [R5 识字1000字](bc-c690a517)。
> 判定标准：`.agent_workspace/ROUND5-ACCEPTANCE.md`

记录日期：2026-08-26
集成分支：`cursor/openmoji-integration-9f67` @ `8738db4`（合并后）
回归基线实测：[R5 回归门禁](bc-0e8710a4) @ `aacd996`（test:round3 + Lighthouse）

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | PASS | 合并绘本/成语/母题/小游戏后 |
| G2 | Round 5 硬门槛 | `npm run check:round5` | **5/6** | 仅 H1 字库 500/1000 FAIL |
| G3 | Round 3 全链 | `npm run test:round3` | PASS | 回归分支实测退出码 0 |
| G4 | 出包 | `npm run build:all` | PASS | 基线 zip 见 §4 |
| G5 | Lighthouse | `npm run test:acceptance` | PASS | 识字 96/100/100，数学 96/100/100（回归分支） |

## 1. `check:round5` 六项硬门槛（当前）

| # | 检查 | 阈值 | 实测 |
| --- | --- | --- | --- |
| H1 | 字库 | ≥ 1000 | **500** ❌ |
| H2 | 绘本 + 零越界 | ≥ 30 | **30** ✅ |
| H3 | 成语 | ≥ 60 | **60** ✅ |
| H4 | 母题 | ≥ 100 | **118** ✅ |
| H5 | 数形演示 | ≥ 7 | **8** ✅ |
| H6 | 新小游戏 | ≥ 3 | **3** ✅（迷宫/配对/找不同） |

探针待接：L-M6 字源 ≥50 字；教具路径探针与实现对齐（功能已落地）。

## 2. Round 3 回归（回归分支 @ aacd996）

- `npm run test:round3` 退出码 0
- axe 20/20 路由 + 识字 42 交互态 `critical=0` / `serious=0`
- 修复：axe keep-alive 清理；庆祝层 lazy-load smoke 时序

## 3. Lighthouse（回归分支 @ aacd996）

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 | 96 | 100 | 100 |
| 数学 | 96 | 100 | 100 |

## 4. 基线 zip（回归分支 @ aacd996，合并前）

| 文件 | 大小（bytes） |
| --- | ---: |
| `dist/hongen-literacy-app.zip` | 1,014,656 |
| `dist/hongen-math-app.zip` | 202,253 |

合并 30 绘本/小游戏后需重打 zip 更新本节。

## 5. 结论

Round 5 内容 **差 H1 即可闭合**；Round 3 / 构建 / Lighthouse 基线已由 [R5 回归门禁](bc-0e8710a4) 固化。
