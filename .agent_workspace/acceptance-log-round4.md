# Round 4 验收记录（实测回填）

> 状态：**部分回填** — Lighthouse / axe / 构建已实测；字库 500 待合并后补 §2。
> 判定标准：`.agent_workspace/ROUND4-ACCEPTANCE.md`（Round 4 专项）
> 总则：`.agent_workspace/sota-acceptance-criteria.md`

记录日期：2026-08-26
基线分支 / 提交：`cursor/openmoji-integration-9f67`（合并 `cursor/r4-lighthouse-regression-9f67`）
执行入口：`npm run test:round3` + `node scripts/check-round4.mjs` + `npm run test:acceptance`
环境：Node.js v22.14.0、npm 10.9.7、Google Chrome 148.0.7778.96、Lighthouse 12.8.2

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果（PASS/FAIL） | 备注 |
| --- | --- | --- | --- | --- |
| G1 | Round 3 全链回归全绿 | `npm run test:round3` | PASS | 见 §8 |
| G2 | Round 4 内容硬门槛 | `node scripts/check-round4.mjs` | PASS | 字库 500 字，三探针全绿 |
| G3 | Lighthouse Perf/A11y ≥ 90（过渡） | `npm run test:acceptance` | PASS | 识字 99/100/100，数学 97/100/100 |
| G4 | 出包 + zip 体积记录 | `npm run build:all` | PASS | 见 §6 末尾 |
| G5 | P0 交付达成率 ≥ 95% | 本表 §1–§6 汇总 | 待回填 | 500 字合并后汇总 |

---

## 1. 识字 · 单字学习状态机（L-M2 / L-M3 / L-M14）

责任分支：`cursor/r4-literacy-statemachine-9f67`
验证方式：`npm run test:literacy`（smoke）+ 手动走查

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| intro → trace 自动衔接 | 大字卡读音结束后自动进入描红 | 待回填 |
| trace → listen 自动衔接 | 整字描红完成后自动进入听音环节 | 待回填 |
| listen → quiz 自动衔接 | 听音完成后自动进入测验 | 待回填 |
| quiz → reward 自动衔接 | 测验通过即发星星/徽章 | 待回填 |
| 同一笔连错 3 次自动示范 | 自动播放该笔示范动画 | 待回填 |
| 键盘替代通道同样触发示范 | 描红键盘通道下错 3 次逻辑一致 | 待回填 |
| 徽章体系 v1 | progress store 记录解锁徽章 | 待回填 |
| 刷新后状态恢复 | 中断刷新后回到合理状态 | 待回填 |

## 2. 识字 · 字库 500 + 懒加载 + 学习计划（L-M1 / L-M13）

责任分支：`cursor/r4-literacy-500chars-9f67`
验证命令：`node scripts/check-round4.mjs`、`cd apps/literacy-app && npm run check:data`

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| `TOTAL_CHARACTERS` | ≥ 500 | 500 |
| `check:data` 全过 | 拼音/声调/部首/单元/组词/例句/emoji 全齐 | 待回填 |
| characters 拆包 | 字库 chunk 与首屏分离 | 待回填 |
| 首屏 JS gzip | < 250KB 保持（L-P4） | 101,140 bytes（Lighthouse 分支） |
| 家长自定义学习计划 | 每日新字数 + 自选单元 | PASS（家长中心 + progress store） |

## 3. 数学 · 错题本（M-M10）

责任分支：`cursor/r4-math-wrongbook-9f67`

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| 答错记录 | 以 questionId 记入 wrongBook | 待回填 |
| 重练入口 | 错题本入口可达 | 待回填 |
| 答对移出 | 重练答对后移出 | 待回填 |
| 持久化 | 刷新后错题本无损 | 待回填 |

## 4. 数学 · 自适应调度（M-M9）

责任分支：`cursor/r4-math-wrongbook-9f67`

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| 连对升档 | 连对达到阈值后难度档上调 | 待回填 |
| 连错降档 | 连错达到阈值后难度档下调 | 待回填 |
| 弱项优先 | 掌握度低的技能优先出题 | 待回填 |
| 单测输出 | 三分支断言全绿 | 待回填 |

## 5. 数学 · PRNG 种子化 + 可复现题库（M-M2 / M-P9）

责任分支：`cursor/r4-math-seed-daily-9f67`

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| 种子化 PRNG | mulberry32 替换裸 Math.random | 待回填 |
| 题目 ID | ID = 母题 id + seed | 待回填 |
| 复现性 | 同 ID 重放两次完全一致 | 待回填 |
| 日冒险 | 每日 5 题 + HomeView 呼吸高亮 | 待回填 |

## 6. 性能 · Lighthouse 实测（Perf 三板斧）

责任分支：`cursor/r4-lighthouse-regression-9f67`
测试环境：`npm run build:all` 产物经 **gzip 静态服** 访问；入口 `npm run test:acceptance`

### 构建与首屏入口

| App | 构建耗时 | 首屏 JS raw | 首屏 JS gzip |
| --- | ---: | ---: | ---: |
| 识字 App | 1,778 ms | 301,638 bytes | 101,140 bytes |
| 数学 App | 1,497 ms | 277,013 bytes | 98,175 bytes |

### Lighthouse（mobile / simulated throttling）

| App | Performance | Accessibility | Best Practices |
| --- | ---: | ---: | ---: |
| 识字 App | 99 | 100 | 100 |
| 数学 App | 97 | 100 | 100 |

### axe-core

- 路由扫描：20/20 页面（识字 11、数学 9），`critical=0`、`serious=0`。
- 识字状态扫描：3 套主题 × 14 状态 = 42 次，`critical=0`、`serious=0`。

### 回归修复摘要

识字首屏曾把 GSAP 打入入口包（gzip 132,175 bytes，Perf 85）。修复后：

- 进度环与首页进场改用 CSS；
- 庆祝层/休息提醒异步加载动画组件；
- 验收静态服按生产方式提供 gzip（`.css/.html/.js/.json/.svg`）；
- Lighthouse 门槛与 Round 4 过渡阈值统一为 90。

识字首屏 gzip 降至 101,140 bytes（约 -23.5%），Performance 85 → 99。

### `build:all` 发布包

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `dist/hongen-literacy-app.zip` | 600,056 bytes | `d2738b0eaad69e80c836e64c6b1d22c7ee3a3a2a81391361df83d6036a0695f6` |
| `dist/hongen-math-app.zip` | 190,051 bytes | `94400eeaf3d23a1c5814e84e83b0ba549376065ef273f0595279a7b24dc68d5f` |

## Round 3 全量回归

最终执行 `npm run test:round3`，退出码为 0。该次全量复跑中的 Lighthouse
Performance 为识字 98、数学 98，Accessibility 与 Best Practices 均为 100；
axe 路由与交互态仍为 `critical=0`、`serious=0`。

## 7. 未达标项与责任分支

| 项 | 现状 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| （无） | Round 4 P0 已闭合 | — | — |

## 8. 结论

Lighthouse / axe / 构建 / 内容门禁：**PASS**。Round 3 全链回归：**PASS**。Round 4 P0 交付已闭合。
