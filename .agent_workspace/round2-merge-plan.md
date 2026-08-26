# Round 2 双App代码归并计划（审计 + 执行指令）

- 审计者：fable 子代理（claude-fable-5-thinking-xhigh）
- 审计基准：commit `9f8904d`（分支 `cursor/hongen-edu-apps-9f67`）
- 执行者：opus-fast 子代理
- 审计方法：从入口（index.html → main.js → App.vue → router）+ 各 App scripts/ 测试脚本出发，
  用 rg 全仓抓取 import/动态 import，构建完整引用图；对每个零入边文件人工复核内容后给出决策。

## ⚠️ 前置警告：并发写树

本轮有 10 个子代理**共享同一分支与同一工作树**。审计期间已观察到在制品：
`QuizShell.vue` + `errorTags.js`（math）、`sw.js` + `vite-offline-plugin.mjs`（双App离线）、
`useVoiceStatus.js` + `VoiceNotice.vue` + `CelebrationOverlay.vue`（literacy）、字库扩展（characters/radicals.js）。
已核实：**上述在制品均不引用本计划的任何待删文件**（rg 无命中）。
执行时必须：
1. 动手前重跑本文末尾的「守卫命令」，确认待删文件仍是零引用；
2. 只 `git add` 明确列出的文件，**严禁 `git add -A` / `git add .`**（会把其他代理的 WIP 卷进提交）；
3. push 被拒时 `git pull --rebase --autostash origin cursor/hongen-edu-apps-9f67` 后重试。

## 对 Round1 简报的三处修正（勿超删！）

| 简报原文 | 实际情况 |
| --- | --- |
| "math `core/engine/*` 未引用" | **`core/engine/adaptive.js` 在用**：`stores/progress.js` 引入 `updateMastery`/`MASTERY_THRESHOLD`，是掌握度模型核心。仅 sudoku/generator/wordproblem 三个死。 |
| "math `src/views/*` 未引用" | **`src/views/HomeView.vue` 在用**：路由 `/` 的目标。旧的 7 个 views（CountingView 等）已在 Round1 commit `a114700` 删除。 |
| "literacy `HomeMap/Books.vue` 等死代码" | 已在 Round1 commit `6bbf99e` 删除（HomeMap.vue、CharacterLearn.vue）。**当前 literacy src 无死文件**。 |

## 决策表

### math-app（6 个死文件，共 499 行，全部零入边）

| 文件 | 行数 | 决策 | 理由 |
| --- | --- | --- | --- |
| `src/core/engine/generator.js` | 129 | **删除** | randInt/shuffle/distractors 已被在用的 `utils/random.js`（numericOptions 含错因偏移）覆盖；其「题目协议」设计已由在制品 QuizShell + `data/errorTags.js` 以更完整形态落地。 |
| `src/core/engine/wordproblem.js` | 44 | **删除** | 模板实例化（参数采样+皮肤填充）被在用 `data/wordProblems.js` 的 make() 闭包模式取代，后者还多出 hint/equation/unit/visual 字段。 |
| `src/core/engine/sudoku.js` | 110 | **删除，但先摘录** | 在用 `utils/sudoku4.js` 仅 4×4；此文件的 `BOARD_SPECS`（4/6/9 三档宫格布局）对应 curriculum.js 已规划的 sudoku-6/sudoku-9 技能点。删除前把 BOARD_SPECS 思路记入本文件附录（已抄，见下），未来实现 6/9 宫时从 git 恢复或重写。 |
| `src/core/canvas/stage.js` | 66 | **删除** | Canvas 渲染基座，当前无任何 canvas 玩法；Round2 P0 不含七巧板/迷宫。需要时 `git show 9f8904d:apps/math-app/src/core/canvas/stage.js` 恢复。 |
| `src/data/word-problems.js` | 76 | **删除** | 4 母题骨架（WP_TEMPLATES），是在用 `data/wordProblems.js`（16 母题、WORD_PROBLEMS）的真子集且字段更弱。注意两文件仅差一个连字符，删错即致命——删带连字符的那个。 |
| `src/composables/usePointerDrag.js` | 74 | **删除** | 全仓无引用；当前所有玩法均为点选交互，无拖拽。 |

### math-app 保留项（曾被怀疑，经查在用）

| 文件 | 状态 |
| --- | --- |
| `src/core/engine/adaptive.js` | 保留。stores/progress.js 引用。 |
| `src/core/audio/sound.js` | 保留。全部视图引用。Round2 P1 的 Tone→WebAudio 瘦身应**保 API 换实现**，不动调用方。 |
| `src/utils/sound.js` | 保留。是门面（统一静音开关），非重复实现。 |
| `src/views/HomeView.vue` | 保留。路由 `/` 目标。 |
| `src/utils/sudoku4.js` | 保留。SudokuView 与 scripts/check-content.mjs 双重引用。 |

### math-app 配套修改（与删除同一提交）

1. `README.md`（math）第 52 行提及 `usePointerDrag` —— 删掉该句。
2. `src/data/curriculum.js` 第 52 行注释 `M6 应用题(引用 word-problems.js 模板)` → 改为 `wordProblems.js`；
   四个技能点的 `params: { template: 'combine'|'remain'|'diff'|'times' }` 指向已删模板 id 且**全仓无消费方**（已核实），
   直接删除这四处 `params.template`，避免误导后续代理。

### literacy-app（无删除动作）

| 文件 | 决策 | 理由 |
| --- | --- | --- |
| `src/utils/srs.js` | **保留（重点）** | 应用侧零引用，但被 `scripts/test-srs.mjs` 测试覆盖（最新提交 9f8904d 刚扩了用例），且是 Round2 P0#2「FSRS 接线」的目标文件。**不是死代码，是待接线资产。** |
| `src/utils/sfx.js` / `speech.js` | 保留不动 | 21 行门面包装 `utils/audio.js`。views 走门面、App/components 直连 audio.js 的路径不一致属 P2 美化，且并发代理正在改 audio.js，本轮**不动**以避冲突。 |
| 其余 35 个 src 文件 | 保留 | 全部在引用图内（10 视图入路由、8 组件、4 数据、2 store、theme.css 经 base.css @import）。 |

### 跨 App 重复（本轮不合并）

MascotCompanion vs MascotBot、StarBurst vs StarField、两套 progress store、两套音效栈——
形似但业务语义已分叉，抽到 shared/ 的收益低于回归风险。Round2 仅按 P0#3 做设计令牌迁移
（literacy theme.css → shared/design-tokens.css），组件级共享留给 Round3 评估。

## 归并执行顺序（opus-fast 按序执行）

**步骤 0 — 守卫（必做）**

```bash
cd /workspace && git pull --rebase --autostash origin cursor/hongen-edu-apps-9f67
rg -n "core/engine/(sudoku|generator|wordproblem)|core/canvas|data/word-problems|usePointerDrag" \
   apps --glob '!**/dist/**' --glob '!**/node_modules/**'
```

期望：只命中待删文件自身、README.md 与 curriculum.js 的注释、`.agent_workspace/` 历史文档。
若命中任何 **新的 src 引用**（说明并发代理接了这些文件），立即中止并重估。

**步骤 1 — 纯删除（commit 1，零功能风险）**

```bash
git rm apps/math-app/src/core/engine/sudoku.js \
       apps/math-app/src/core/engine/generator.js \
       apps/math-app/src/core/engine/wordproblem.js \
       apps/math-app/src/core/canvas/stage.js \
       apps/math-app/src/data/word-problems.js \
       apps/math-app/src/composables/usePointerDrag.js
```

同提交内完成配套修改（README、curriculum.js 注释与 params.template）。
提交信息建议：`chore(math): 删除零引用的并行开发遗留实现（engine/canvas/旧母题库）`。
**只 add 上述 8 个文件路径。**

**步骤 2 — 验证后立即 push**

```bash
cd apps/math-app && npm run check:content && npm run build && npm run smoke
cd /workspace && git push -u origin cursor/hongen-edu-apps-9f67
```

check:content 经 register-alias.mjs 直接以 Node 加载 src（不走 Vite），能兜住脚本层断链；
build + smoke 兜住应用层断链。任一失败先查是否并发代理改动所致，勿盲目回滚他人文件。

**步骤 3 —（可选 P1，独立提交）数独多规格合并**

仅当 Round2 排期实现 6/9 宫时执行：将 `utils/sudoku4.js` 泛化为按 `BOARD_SPECS` 参数化
（见附录），保持 `generatePuzzle/solve/conflictsOf/nextHint/isSafe` 导出签名不变；
若改文件名，必须同步 `SudokuView.vue` 与 `scripts/check-content.mjs` 两处 import。
未排期则跳过，不要为未来需求预留死代码。

**步骤 4 — literacy 无归并动作。** FSRS 接线属 P0#2 独立任务，不在本计划内。

## 风险清单（按严重度排序）

1. **并发写树竞态**：其他代理可能在你执行期间新增对待删文件的引用。缓解：步骤 0 守卫必做、
   删除到 push 的窗口压到最短、只 add 白名单路径。
2. **同名陷阱**：`word-problems.js`（删）与 `wordProblems.js`（保）只差连字符；`core/engine/sudoku.js`（删）
   与 `utils/sudoku4.js`（保）同名异位。逐一核对 `git rm` 路径。
3. **简报失真导致超删**：adaptive.js、views/HomeView.vue、utils/sound.js 看似可疑实则在用，
   已列入保留表，不得删除。
4. **check-content.mjs 以相对路径直连 src**：它不经打包器，Vite build 通过不代表脚本没断，
   两条验证都要跑。
5. **9×9 数独生成性能**（仅步骤 3 相关）：挖洞唯一解校验为指数级回溯，低端设备需保留
   clue 下限 + countSolutions 早停 limit=2，并考虑 Web Worker。
6. **文档诱导复活**：`.agent_workspace/math-architecture.md` 仍描述 engine 层架构。已在本文声明：
   题目协议以在制品 QuizShell + errorTags.js 实现为准，后续代理勿按旧文档重建 core/engine。

## 附录：core/engine/sudoku.js 中值得未来复用的设计（删除前摘录）

```js
// 三档宫格布局：size=边长, boxW/boxH=宫的宽高（6×6 是 3×2 宫）
export const BOARD_SPECS = {
  4: { size: 4, boxW: 2, boxH: 2 },
  6: { size: 6, boxW: 3, boxH: 2 },
  9: { size: 9, boxW: 3, boxH: 3 },
}
// 生成流程：随机化回溯填满整盘 → 按乱序挖洞 → 每挖一格用解计数器（上限2）验证唯一解
```

在用 `utils/sudoku4.js` 的挖洞唯一解校验逻辑与此一致（仅棋盘参数写死 4×4），
泛化时以 sudoku4.js 为基（其 nextHint/conflictsOf 是 UI 实际依赖），引入 BOARD_SPECS 即可。
完整原文：`git show 9f8904d:apps/math-app/src/core/engine/sudoku.js`
