# Round 4 验收标准 —— P0 清零 + 核心闭环

> 版本：Round 4 v1.0（2026-08-26）
> 依据：`.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md` §5「Round 4」+ §6 任务分配、`.agent_workspace/ROUND4-BRIEF.md`
> 配套：`.agent_workspace/sota-acceptance-criteria.md`（SOTA 全量标准，Round 4 不重复罗列）、`.agent_workspace/acceptance-log-round4.md`（实测回填模板）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
| --- | --- | --- | --- |
| G1 | Round 3 全链回归 | `npm run test:round3` | 全绿（识字/数学单测 + 构建 + smoke + 离线 + acceptance），Round 4 改动不得回归 Round 3 成果（axe critical/serious = 0 等） |
| G2 | Round 4 内容硬门槛 | `node scripts/check-round4.mjs` | 退出码 0（当前基线预期 FAIL：字库 200 < 500，由 r4-literacy-500chars 清零） |
| G3 | Lighthouse | `npm run test:acceptance`（gzip 静态服 + 4× CPU 节流） | Perf/A11y ≥ **90**（过渡硬门槛）；终值目标 ≥ **95**（L-P1/M-P1/L-A1/M-A1），未达 95 的项列入 §7 未达标表并注明差距 |
| G4 | 出包 | `npm run build:all` | 成功出包，zip 体积回填 acceptance-log §6（D-7：<10MB 级） |
| G5 | 总达成率 | acceptance-log-round4.md 汇总 | P0 交付（§1–§3）达成率 ≥ **95%**；日志全部实测回填，无「待回填」残留 |

---

## 1. 识字 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| L-M2 | 单字学习状态机 | `CharDetailView` 内 `intro→trace→listen→quiz→reward` 五态**自动衔接**：每一环完成后无需手动切页即进入下一环；中途退出/刷新后状态合理恢复，已发奖励不丢失 | smoke + 手动走查（acceptance-log §1 逐项勾） | r4-literacy-statemachine |
| L-M3 | 错 3 次自动示范 | 描红时**同一笔**连错 3 次，自动播放该笔示范动画（HanziStrokeBox），随后允许重试**该笔**而非整字重来；键盘替代通道行为一致 | 手动走查（含键盘通道） | r4-literacy-statemachine |
| L-M14 | 徽章体系 v1 | progress store 持久化徽章解锁记录；成就页展示已解锁/未解锁两态；解锁庆祝可跳过（D-6） | smoke + localStorage 检查 | r4-literacy-statemachine |
| L-M1 | 字库 200→500 + 懒加载 | ① `TOTAL_CHARACTERS ≥ 500`，`check:data` 全过（字段齐全、单元归属、与 `shared/data/common-hanzi.json` 基线一致）；② `characters.js` 经路由级/动态 import 懒加载，**不进首屏 chunk**；③ 首屏 JS gzip < 250KB 保持 | `node scripts/check-round4.mjs` + `check:data` + dist chunk 清单 | r4-literacy-500chars |
| L-M13 | 家长自定义学习计划 | 家长中心可设**每日新字数**与**自选单元**；设置持久化；首页「今日任务」按计划出字 | 手动走查 + 刷新验证 | r4-literacy-500chars |

## 2. 数学 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| M-M10 | 错题本 | 答错按 `questionId` 记入 `wrongBook`；错题本入口可达并支持重练；**重练答对即移出**；刷新/重开后无损 | smoke + 手动走查 | r4-math-wrongbook |
| M-M9 | 自适应调度器 | `adaptive.js`：连对达到阈值**升档**、连错达到阈值**降档**、掌握度（EMA）弱项**优先出题**；三分支各有单测断言 | 单测 + 实机走查 | r4-math-wrongbook |
| M-M2 / M-P9 | 种子化 PRNG + 可复现题库 | mulberry32（或等价）替换出题路径裸 `Math.random`；题目 ID = 母题 id + seed，**同 ID 重放题面/选项/答案完全一致**；check 门禁校验 ≥ **300** 道可复现题 | `check:content` 扩展 + 单测（复现断言） | r4-math-seed-daily |
| M-M12 | 日冒险 + 当前关高亮 | 每日 5 题冒险入口（当日完成态持久化）；HomeView 当前关**呼吸高亮**，`prefers-reduced-motion` 与家长动效开关下降级为静态高亮 | 手动走查 | r4-math-seed-daily |
| M-M4 | 比较模块入口 | 比较玩法入口可达（独立模块或并入 number-sense），有判定与反馈，键盘可完成 | smoke + 手动走查 | r4-math-seed-daily |

## 3. 共同 P0 交付与 PASS 标准

| 编号 | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| C-R4-1 | Perf 三板斧 | ① characters 拆包（见 L-M1②）；② 验收链路以 **gzip 静态服**实测；③ 首屏关键 CSS 内联/优先加载；三项落地后 LH Perf ≥ 90（过渡）→ 95 | `npm run test:acceptance` + dist 产物核对 | r4-perf-bundle |
| C-R4-2 | 设计令牌 Phase 2/3 | `check:tokens` Phase 2/3 全 PASS（硬编码色值/尺寸迁移到 `shared/styles/design-tokens.css`） | `npm run check:tokens:wiring` 及 tokens 脚本 Phase 2/3 模式 | r4-tokens-phase23 |
| C-R4-3 | 验收日志 + zip 重打 | `acceptance-log-round4.md` **全部实测回填**（无「待回填」）；`build:all` 重打 zip 并记录体积 | 文档审查 + G4 | r4-lighthouse-regression |

## 4. `scripts/check-round4.mjs` 硬门槛与探针（当前状态）

Round 4 新增内容门禁脚本，随各子代理交付逐步「探针 → 硬门槛」升级：

| 检查 | 当前状态 | 说明 |
| --- | --- | --- |
| 字库 ≥ 500（L-M1） | **硬门槛**（基线 200，预期 FAIL） | r4-literacy-500chars 扩库后转绿 |
| 错题本模块存在（M-M10） | 探针（PENDING，不计失败） | 实现后由责任分支升级为硬门槛（含移出语义断言） |
| `adaptive.js` 存在（M-M9） | 探针（PENDING，不计失败） | 同上（含三分支单测） |
| 种子化 PRNG（M-M2/M-P9） | 探针（PENDING，不计失败） | 实现后升级为「≥300 可复现」硬门槛，接入 `check:content` |

原则：探针只提示不拦截；**功能一旦合入，对应探针必须在同一 PR 内升级为硬门槛**，否则视为未交付。

## 5. 不回归红线（继承自 Round 3，抽查即可）

- axe critical = 0 且 serious = 0（双 App 全路由，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 触控 ≥ 56×56、键盘可达、庆祝可跳过、`prefers-reduced-motion` 降级
- 运行时零第三方域名请求；`THIRD_PARTY_NOTICES` 随新资源同步

## 6. 回填要求

每条 P0 在 `acceptance-log-round4.md` 对应小节必须有**实测数据或命令输出**（分数、计数、日志粘贴、走查勾选）。禁止「应该可以」「理论上通过」。未达标项一律进 §7 未达标表并写明责任分支与计划，不得静默遗漏。
