# Round 5 验收记录（基线实测）

> 状态：**基线回填完成** — Round 3 全链回归全绿；Round 5 六项内容硬门槛按预期保持红灯。
> 判定标准：`.agent_workspace/ROUND5-ACCEPTANCE.md`（Round 5 专项）
> 总则：`.agent_workspace/sota-acceptance-criteria.md`

记录日期：2026-08-26
基线分支 / 提交：`cursor/openmoji-integration-9f67` @ `aacd996`
执行入口：`npm test` → `npm run check:round5` → `npm run test:round3` → `npm run build:all`
环境：Node.js v22.14.0、npm 10.9.7、Google Chrome 148.0.7778.96、Lighthouse 13.4.1

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测回归全绿 | `npm test` | PASS | 已包含在 G3 全链回归中 |
| G2 | Round 5 内容硬门槛（6 项） | `npm run check:round5` | FAIL（预期） | 1 项辅助校验通过、4 项探针待接线、6 项硬门槛失败 |
| G3 | Round 3 全链回归全绿 | `npm run test:round3` | PASS | 退出码 0，见 §7 |
| G4 | 出包 + zip 体积记录 | `npm run build:all` | PASS | 见 §8 |
| G5 | P0 交付达成率 ≥ 95% | 本表 §1–§6 汇总 | FAIL（预期） | 本记录是 Round 5 内容分支合入前基线 |

## 1. `check:round5` 六项硬门槛

验证命令：`npm run check:round5`（退出码 1）

| # | 检查 | 阈值 | 基线实测 |
| --- | --- | --- | --- |
| H1 | 字库 `TOTAL_CHARACTERS` | ≥ 1000 | FAIL：500 |
| H2 | 绘本 `BOOKS.length` + 零越界 | ≥ 30 | FAIL：5；覆盖校验零越界 |
| H3 | 成语 `IDIOMS.length` | ≥ 60 | FAIL：20 |
| H4 | 数学母题 `WORD_PROBLEMS.length` | ≥ 100 | FAIL：34 |
| H5 | 数形演示 `VISUAL_DEMOS` | ≥ 7 类 | FAIL：未接线 |
| H6 | 新识字小游戏 `GAMES`（不含 listen） | ≥ 3 款 | FAIL：注册表未接线 |

Round 5 内容分支尚未合入时，以上六项均为验收规范定义的预期红灯。

## 2. 识字 · 字库 1000 + 懒加载（L-M1）

| 指标 | 要求 | 基线实测 |
| --- | --- | --- |
| `TOTAL_CHARACTERS` | ≥ 1000 | FAIL：500 |
| `check:data` 全过 | 字段与归属完整 | PASS：35/35 |
| 与共享字库基线一致 | 无漂移 | PASS：共享基线 500 字全部匹配 |
| 字库分片懒加载 | `chars/uN.js` 不进首屏 chunk | PASS：33/33 单元分片，首屏无同步课文包 |
| 首屏 JS gzip | < 250KB | PASS：96,216 bytes |

## 3. 识字 · 绘本 30 + 成语 60 + 字源（L-M5 / L-M8 / L-M6）

| 检查点 | 要求 | 基线实测 |
| --- | --- | --- |
| `BOOKS.length` | ≥ 30 | FAIL：5 |
| `verifyBookCoverage()` | 零越界 | PASS |
| 分级梯度 | level 递进 | PASS：3 个分级 |
| 绘本 smoke | 可完整阅读 | PASS：5 本路由可达，b1 完整翻页 |
| `IDIOMS.length` | ≥ 60 | FAIL：20 |
| 成语结构与详情 | 字段完整、详情可达 | PASS：内容自检及 4 条详情路由通过 |
| 字源动画可演示字数 | ≥ 50 | FAIL：未接线 |

## 4. 识字 · 3 款新小游戏（L-M12）

| 检查点 | 要求 | 基线实测 |
| --- | --- | --- |
| `GAMES` 注册表新增条目 | ≥ 3（不含 listen） | FAIL：未接线 |
| 路由与 smoke | 三款均可达且有断言 | FAIL：尚未交付 |
| 键盘与触控通道 | 三款均可完成 | FAIL：尚未交付 |

## 5. 数学 · 母题 100（M-M3）

| 指标 | 要求 | 基线实测 |
| --- | --- | --- |
| `WORD_PROBLEMS.length` | ≥ 100 | FAIL：34 |
| `check:content` 全过 | 生成、答案、可复现均合法 | PASS |
| 难度分档 | 一步/两步/进阶均覆盖 | PASS（基线内容自检） |

## 6. 数学 · 数形演示 ×7 + 教具三件套（M-M8 / M-M5 / M-M13 / M-M11）

| 检查点 | 要求 | 基线实测 |
| --- | --- | --- |
| `VISUAL_DEMOS` 注册表 | ≥ 7 类 | FAIL：未接线 |
| 七巧板 v1 | ≥ 3 目标图形 + 键盘通道 | FAIL：未接线 |
| 分与合 v1 | `compose-ten` + 练习判定 | FAIL：未接线 |
| 竖式专题 v1 | 进位/借位错因入口 | FAIL：未接线 |

## 7. Round 3 全链回归

执行命令：`npm run test:round3`，最终退出码 0。

| 检查 | 要求 | 基线实测 |
| --- | --- | --- |
| 识字自动化 | 全绿 | PASS：FSRS 8/8、内容 35/35、21 路由 + 18 交互 |
| 数学自动化 | 全绿 | PASS：内容自检、构建、smoke |
| Lighthouse 识字 Perf/A11y/BP | ≥ 90/90 | PASS：96 / 100 / 100 |
| Lighthouse 数学 Perf/A11y/BP | ≥ 90/90 | PASS：96 / 100 / 100 |
| axe 全路由 + 交互态 | critical=0、serious=0 | PASS：20/20 路由 + 3 主题 × 15 状态 |
| 离线 smoke | 断网冷启动闭环 | PASS：双 App |

## 8. 构建产物

`npm run build:all` 退出码 0。

| 文件 | 大小（bytes） | SHA-256 |
| --- | ---: | --- |
| `dist/hongen-literacy-app.zip` | 1,014,656 | `20c4bcf4f626f3185c4b03456a29b3ff0089e3c6b994809325e83356be4208cc` |
| `dist/hongen-math-app.zip` | 202,253 | `344b5246744718230a69e319fc15ce13d9d0ac88d13bf8daa0439923f7dbecb0` |

| App | 首屏 JS raw | 首屏 JS gzip |
| --- | ---: | ---: |
| 识字 App | 274,957 bytes | 96,216 bytes |
| 数学 App | 287,452 bytes | 102,270 bytes |

## 9. 未达标项与责任分支

| 项 | 基线现状 | 责任分支 |
| --- | --- | --- |
| H1 字库 1000 | 500 | `r5-literacy-1000chars` |
| H2 绘本 30 | 5 | `r5-literacy-books` |
| H3 成语 60 | 20 | `r5-literacy-idioms-etymology` |
| H4 数学母题 100 | 34 | `r5-math-problems-100` |
| H5 数形演示 7 类 | 未接线 | `r5-math-manipulatives` |
| H6 新识字小游戏 3 款 | 未接线 | `r5-literacy-minigames` |

## 10. 结论

Round 4 闭合态回归、Lighthouse 与出包均为 **PASS**。Round 5 六项内容门槛在 `aacd996` 基线为**预期 FAIL**，应由对应内容分支逐项清零。

本轮同时修复两处门禁稳定性问题：axe 路由扫描关闭服务器时清理 Chrome keep-alive 连接，以及识字 smoke 等待懒加载庆祝层就绪，避免挂起或时序误报。
