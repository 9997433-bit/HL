# Round 4 验收记录（实测回填模板）

> 状态：**模板** —— 各子代理交付后逐节回填实测数据，禁止填「应该可以」。
> 判定标准：`.agent_workspace/ROUND4-ACCEPTANCE.md`（Round 4 专项）
> 总则：`.agent_workspace/sota-acceptance-criteria.md`
> 主计划原则 4：Brief 里的数字必须实测，写进简报不跑脚本视为未交付。

记录日期：＿＿＿＿（回填时更新）
基线分支 / 提交：＿＿＿＿
执行入口：`npm run test:round3` + `node scripts/check-round4.mjs` + `npm run test:acceptance`

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果（PASS/FAIL） | 备注 |
| --- | --- | --- | --- | --- |
| G1 | Round 3 全链回归全绿 | `npm run test:round3` | 待回填 | 单测 + 构建 + smoke + 离线 + acceptance |
| G2 | Round 4 内容硬门槛 | `node scripts/check-round4.mjs` | 待回填 | 当前基线预期 FAIL（字库 200 < 500） |
| G3 | Lighthouse Perf/A11y ≥ 90（过渡） | `npm run test:acceptance` | 待回填 | 终值目标 ≥ 95，见 §6 |
| G4 | 出包 + zip 体积记录 | `npm run build:all` | 待回填 | 体积填 §6 末尾 |
| G5 | P0 交付达成率 ≥ 95% | 本表 §1–§6 汇总 | 待回填 | 未达标项列 §7 |

---

## 1. 识字 · 单字学习状态机（L-M2 / L-M3 / L-M14）

责任分支：`cursor/r4-literacy-statemachine-*`
验证方式：`npm run test:literacy`（smoke）+ 手动走查（建议录屏留档）

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| intro → trace 自动衔接 | 大字卡读音结束后自动进入描红，无需手动切页 | 待回填 |
| trace → listen 自动衔接 | 整字描红完成后自动进入听音环节 | 待回填 |
| listen → quiz 自动衔接 | 听音完成后自动进入测验 | 待回填 |
| quiz → reward 自动衔接 | 测验通过即发星星/徽章，庆祝可跳过 | 待回填 |
| 同一笔连错 3 次自动示范 | 自动播放**该笔**示范动画后允许重试该笔（非整字重来） | 待回填 |
| 键盘替代通道同样触发示范 | 描红键盘通道下错 3 次逻辑一致 | 待回填 |
| 徽章体系 v1 | progress store 记录解锁徽章；成就页展示已解锁/未解锁 | 待回填 |
| 刷新后状态恢复 | 中断刷新后回到合理状态（不丢已获奖励） | 待回填 |

## 2. 识字 · 字库 500 + 懒加载 + 学习计划（L-M1 / L-M13）

责任分支：`cursor/r4-literacy-500chars-*`
验证命令：`node scripts/check-round4.mjs`、`cd apps/literacy-app && npm run check:data`、`npm run build` 后检查产物 chunk

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| `TOTAL_CHARACTERS` | ≥ 500 | 待回填 |
| `check:data` 全过 | 拼音/声调/部首/单元/组词/例句/emoji 全齐，且与 `shared/data/common-hanzi.json` 基线一致 | 待回填 |
| characters 拆包 | `characters.js` 不进首屏 chunk（路由级/动态 import 懒加载） | 待回填（粘贴 dist chunk 清单） |
| 首屏 JS gzip | < 250KB 保持（L-P4） | 待回填 |
| 家长自定义学习计划 | 每日新字数 + 自选单元可设，持久化并驱动首页「今日任务」 | 待回填 |

`check-round4.mjs` 输出粘贴处：

```text
待回填
```

## 3. 数学 · 错题本（M-M10）

责任分支：`cursor/r4-math-wrongbook-*`
验证方式：`npm run test:math`（smoke）+ 手动走查

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| 答错记录 | 以 `questionId` 记入 `wrongBook`（含错因/时间） | 待回填 |
| 重练入口 | 错题本入口可达，可对单题重练 | 待回填 |
| 答对移出 | 重练答对后该题从错题本移出 | 待回填 |
| 持久化 | 刷新/重开浏览器后错题本无损 | 待回填 |

## 4. 数学 · 自适应调度（M-M9）

责任分支：`cursor/r4-math-wrongbook-*`
验证方式：`adaptive.js` 单测（三分支全覆盖）+ 实机走查

| 检查点 | 预期 | 实测 |
| --- | --- | --- |
| 连对升档 | 连对达到阈值后难度档上调 | 待回填 |
| 连错降档 | 连错达到阈值后难度档下调 | 待回填 |
| 弱项优先 | 掌握度（EMA）低的技能优先出题 | 待回填 |
| 单测输出 | 三分支断言全绿 | 待回填（粘贴输出） |

## 5. 数学 · PRNG 种子化 + 可复现题库（M-M2 / M-P9）

责任分支：`cursor/r4-math-seed-daily-*`
验证命令：`cd apps/math-app && npm run check:content`（含 seed 复现断言后）

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| 种子化 PRNG | mulberry32（或等价）替换生成路径中的裸 `Math.random` | 待回填 |
| 题目 ID | ID = 母题 id + seed，可从 ID 完整重放题面 | 待回填 |
| 复现性 | 同 ID 重放两次，题面/选项/答案完全一致 | 待回填 |
| 题库门禁 | ≥ 300 道可复现题通过 check 校验 | 待回填 |
| 日冒险 | 每日 5 题入口 + HomeView 当前关呼吸高亮（reduced-motion 降级） | 待回填 |

`check:content` 输出粘贴处：

```text
待回填
```

## 6. 性能 · Lighthouse 实测（Perf 三板斧）

责任分支：`cursor/r4-perf-bundle-*` / `cursor/r4-lighthouse-regression-*`
测试环境：`npm run build:all` 产物经 **gzip 静态服** 访问，4× CPU 节流；入口 `npm run test:acceptance`

三板斧核对：

| 手段 | 预期 | 实测 |
| --- | --- | --- |
| characters 拆包 | 字库 chunk 与首屏分离 | 待回填 |
| gzip 静态服 | 验收链路以 gzip 传输实测 | 待回填 |
| 关键 CSS | 首屏关键样式内联/优先加载 | 待回填 |

Lighthouse 分数（过渡硬门槛 ≥ 90，终值目标 ≥ 95）：

| App | Performance | Accessibility | Best Practices | FCP | LCP | TBT | CLS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 识字 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 |
| 数学 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 | 待回填 |

zip 体积（`build:all` 重打后）：识字 ＿＿ MB / 数学 ＿＿ MB（D-7：Web zip <10MB 级）

## 7. 未达标项与责任分支

| 项 | 现状 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| 待回填 | | | |

## 8. 结论

待回填（PASS / FAIL + 一句话依据）。
