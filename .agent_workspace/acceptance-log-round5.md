# Round 5 验收记录（基线）

> 状态：**基线实测完成** — Round 3 全链回归全绿；Round 5 内容门禁按预期保持红灯。
> 依据：`.agent_workspace/ROUND5-BRIEF.md`；实测时 Round 5 专项验收规范分支尚未发布，本文件先提供最小可执行记录。

记录日期：2026-08-26
业务代码基线：`cursor/openmoji-integration-9f67` @ `aacd996`
执行入口：`npm run test:round3`、`npm run check:round5`、`npm run build:all`
环境：Node.js v22.14.0、npm 10.9.7、Google Chrome 148.0.7778.96、Lighthouse 13.4.1

## 1. 门禁总览

| 门禁 | 结果 | 实测摘要 |
| --- | --- | --- |
| Round 3 全链回归 | PASS | 退出码 0；单测、构建、smoke、离线与 acceptance 全绿 |
| Round 5 内容硬门槛 | FAIL（预期） | 0 项通过，5 项失败；见 §3 |
| 生产构建与 zip | PASS | 双 App 构建、zip 完整性检查通过；见 §4 |
| Lighthouse | PASS | 双 App 三项分数均 ≥ 90；见 §5 |

## 2. `test:round3` 基线

`npm run test:round3` 最终退出码为 0：

- 识字：FSRS 8/8、内容自检 35/35、21 条路由 + 18 项交互均通过；
- 数学：内容自检、构建与 smoke 均通过；
- 离线冷启动双 App 均通过；
- 首屏 JS gzip：识字 96,216 bytes、数学 102,270 bytes，均低于 256,000 bytes；
- axe：双 App 20/20 路由及识字 3 套主题 × 15 个交互态均为 `critical=0`、`serious=0`；
- acceptance 总结：所有已执行自动化门槛均通过。

## 3. `check:round5` 基线

`npm run check:round5` 退出码为 1，0 项通过、5 项失败：

1. 字库 500 字，要求 ≥ 1000；
2. 绘本 5 本，要求 ≥ 30；
3. 成语 20 个，要求 ≥ 60；
4. 应用题母题 34 个，要求 ≥ 100；
5. 数形演示未接线，期望 `apps/math-app/src/data/visualDemos.js` 或等价注册表。

以上均是 Round 5 内容分支尚未合入时的预期缺口。

## 4. 基线 zip 体积

| 文件 | 大小（bytes） | SHA-256 |
| --- | ---: | --- |
| `dist/hongen-literacy-app.zip` | 1,014,656 | `20c4bcf4f626f3185c4b03456a29b3ff0089e3c6b994809325e83356be4208cc` |
| `dist/hongen-math-app.zip` | 202,253 | `344b5246744718230a69e319fc15ce13d9d0ac88d13bf8daa0439923f7dbecb0` |

## 5. Lighthouse 基线

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 App | 96 | 100 | 100 |
| 数学 App | 96 | 100 | 100 |

## 6. 结论与待闭合项

Round 4 闭合态回归为 **PASS**，构建体积与 Lighthouse 基线已固化。Round 5 内容门禁为**预期 FAIL**；后续合入内容分支后应逐项清零上述 5 项。

本轮同时修复两处回归门禁稳定性问题：axe 路由扫描关闭服务器时清理 Chrome keep-alive 连接，以及识字 smoke 等待懒加载庆祝层就绪，避免挂起或时序误报。
