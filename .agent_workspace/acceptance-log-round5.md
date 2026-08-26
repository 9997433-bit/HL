# Round 5 验收记录（实测回填）

> 状态：**模板 — 全部待回填**（由 r5-regression-gate 在各子代理合并后实测回填）
> 判定标准：`.agent_workspace/ROUND5-ACCEPTANCE.md`（Round 5 专项）
> 总则：`.agent_workspace/sota-acceptance-criteria.md`
> 禁止「应该可以」「理论上通过」——每格填实测数据、命令输出或走查勾选。

记录日期：待回填
基线分支 / 提交：`cursor/openmoji-integration-9f67` @ 待回填
执行入口：`npm test` → `npm run check:round5` → `npm run test:round3` → `npm run build:all`
环境：Node.js 待回填、npm 待回填、Chrome 待回填、Lighthouse 待回填

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果（PASS/FAIL） | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测回归全绿 | `npm test` | 待回填 | |
| G2 | Round 5 内容硬门槛（6 项） | `npm run check:round5` | 待回填 | 粘贴脚本输出到 §1 |
| G3 | Round 3 全链回归全绿 | `npm run test:round3` | 待回填 | 见 §7 |
| G4 | 出包 + zip 体积记录 | `npm run build:all` | 待回填 | 见 §8 |
| G5 | P0 交付达成率 ≥ 95% | 本表 §1–§6 汇总 | 待回填 | |

## 1. `check:round5` 六项硬门槛

验证命令：`npm run check:round5`（退出码 0 才算 PASS）

| # | 检查 | 阈值 | 基线（aacd996） | 实测 |
| --- | --- | --- | --- | --- |
| H1 | 字库 `TOTAL_CHARACTERS` | ≥ 1000 | 500 | 待回填 |
| H2 | 绘本 `BOOKS.length` + 零越界 | ≥ 30 | 5 | 待回填 |
| H3 | 成语 `IDIOMS.length` | ≥ 60 | 20 | 待回填 |
| H4 | 数学母题 `WORD_PROBLEMS.length` | ≥ 100 | 34 | 待回填 |
| H5 | 数形演示 `VISUAL_DEMOS` | ≥ 7 类 | 未接线 | 待回填 |
| H6 | 新识字小游戏 `GAMES`（不含 listen） | ≥ 3 款 | 0 款 | 待回填 |

脚本输出粘贴：

```
（待回填：npm run check:round5 完整输出）
```

## 2. 识字 · 字库 1000 + 懒加载（L-M1）

责任分支：`cursor/r5-literacy-1000chars-9f67`
验证命令：`npm run check:round5`、`cd apps/literacy-app && npm run check:data`、dist chunk 清单

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| `TOTAL_CHARACTERS` | ≥ 1000 | 待回填 |
| `check:data` 全过 | 拼音/声调/部首/笔画/单元/emoji 字段齐全 | 待回填 |
| 与 `shared/data/common-hanzi.json` 基线一致 | 无漂移 | 待回填 |
| 字库分片懒加载 | `chars/uN.js` 不进首屏 chunk | 待回填 |
| 首屏 JS gzip | < 250KB 保持 | 待回填 |

## 3. 识字 · 绘本 30 + 成语 60 + 字源（L-M5 / L-M8 / L-M6）

责任分支：`cursor/r5-literacy-books-9f67`、`cursor/r5-literacy-idioms-etymology-9f67`

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| `BOOKS.length` | ≥ 30 | 待回填 |
| `verifyBookCoverage()` | 返回空数组（零越界） | 待回填 |
| 分级梯度 | level 覆盖递进（1 级起步→高级） | 待回填 |
| 翻页走查 | 抽查 ≥ 3 本可完整阅读、发音正常 | 待回填 |
| `IDIOMS.length` | ≥ 60 | 待回填 |
| 成语详情 | 释义/故事/emoji 齐全（抽查 ≥ 5 条） | 待回填 |
| 字源动画可演示字数 | ≥ 50 | 待回填 |
| 字源入口 + 可跳过 + reduced-motion 降级 | 三项全过 | 待回填 |

## 4. 识字 · 3 款新小游戏（L-M12）

责任分支：`cursor/r5-literacy-minigames-9f67`
验证方式：`npm run check:round5`（GAMES 注册表 + 路由接线）+ smoke + 手动走查

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| `GAMES` 注册表新增条目 | ≥ 3（不含 listen） | 待回填 |
| 路由可达 | 每款 route 在 router 接线且可打开 | 待回填 |
| smoke 断言 | 每款至少 1 条 smoke 断言 | 待回填 |
| 键盘可完成 | 每款有键盘替代通道 | 待回填 |
| 触控 ≥ 56×56 / 庆祝可跳过 | 抽查全过 | 待回填 |

## 5. 数学 · 母题 100（M-M3）

责任分支：`cursor/r5-math-problems-100-9f67`
验证命令：`npm run check:round5`、`cd apps/math-app && npm run check:content`

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| `WORD_PROBLEMS.length` | ≥ 100 | 待回填 |
| `check:content` 全过 | 可复现 + 答案正整数 + 字段齐全 | 待回填 |
| 语义类别 `WORD_PROBLEM_TAGS` | 覆盖数与基线对比记录 | 待回填 |
| 分档 `WORD_PROBLEM_TIERS` | 一步/两步/进阶均有新母题 | 待回填 |

## 6. 数学 · 数形演示 ×7 + 教具三件套（M-M8 / M-M5 / M-M13 / M-M11）

责任分支：`cursor/r5-math-manipulatives-9f67`

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| `VISUAL_DEMOS` 注册表 | ≥ 7 类 | 待回填 |
| 三段递进 | 每类实物→图形→算式（逐类走查勾选） | 待回填 |
| 可跳过 + reduced-motion 降级 | 全过 | 待回填 |
| 七巧板 v1 | ≥ 3 目标图形可完成 + 键盘通道 | 待回填 |
| 分与合 v1 | compose-ten 接线 + 练习判定 | 待回填 |
| 竖式专题 v1 | 进位/借位错因入口 + errorTags 归因 | 待回填 |

## 7. Round 3 全链回归

执行命令：`npm run test:round3`

| 检查 | 要求 | 实测 |
| --- | --- | --- |
| 退出码 | 0 | 待回填 |
| Lighthouse 识字 Perf/A11y/BP | ≥ 90/90（终值目标 95） | 待回填 |
| Lighthouse 数学 Perf/A11y/BP | ≥ 90/90（终值目标 95） | 待回填 |
| axe 全路由 + 交互态 | critical=0、serious=0 | 待回填 |
| 离线 smoke | 断网冷启动闭环 | 待回填 |

## 8. 构建产物

执行命令：`npm run build:all`

| 文件 | 大小 | SHA-256 |
| --- | --- | --- |
| `dist/hongen-literacy-app.zip` | 待回填 | 待回填 |
| `dist/hongen-math-app.zip` | 待回填 | 待回填 |

| App | 首屏 JS raw | 首屏 JS gzip（要求 < 250KB） |
| --- | ---: | ---: |
| 识字 App | 待回填 | 待回填 |
| 数学 App | 待回填 | 待回填 |

## 9. 未达标项与责任分支

| 项 | 现状 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| 待回填 | | | |

## 10. 结论

待回填（六项硬门槛 / 回归 / 出包三者全绿才可判 Round 5 闭合）。
