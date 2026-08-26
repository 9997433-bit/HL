# Round 2 双App代码归并计划（审计 + 执行指令）v2

- 审计者：fable 子代理（claude-fable-5-thinking-xhigh）
- 版本：v2（v1 基准 `9f8904d`；v2 已吸收 QuizShell 代理提交 `fd30bc4` 的数独收敛结果）
- 执行者：opus-fast 子代理
- 审计方法：从入口（index.html → main.js → App.vue → router）+ 各 App scripts/ 测试脚本出发，
  用 rg 全仓抓取 import/动态 import，构建完整引用图；对每个零入边文件人工复核内容后给出决策。

## ⚠️ 前置警告：并发写树

本轮有 10 个子代理**共享同一工作树**，且会各自切换分支（审计期间工作树先后处于
`cursor/hongen-edu-apps-9f67` → `cursor/literacy-fsrs-100chars-3265` → `cursor/math-quizshell-2e81`）。
已观察到的在制品/已完成：QuizShell + errorTags + 34 类母题 + 三档数独（`fd30bc4`，已提交）、
离线 SW（`df61fac`，已合并）、literacy 字库扩展与 TTS 兜底（useVoiceStatus/VoiceNotice，在制）。
执行时必须：
1. 动手前重跑「守卫命令」（步骤 0），确认待删文件仍是零引用；
2. 只 `git add` 明确列出的文件，**严禁 `git add -A` / `git add .`**（会把其他代理的 WIP 卷进提交）；
3. **执行基准必须包含 `fd30bc4`**（QuizShell 分支合入主分支之后），否则数独文件状态与本计划不符；
4. push 被拒时 `git pull --rebase --autostash` 后重试。

## 对 Round1 简报的四处修正（勿超删！）

| 简报原文 | 实际情况 |
| --- | --- |
| "math `core/engine/*` 未引用" | **`adaptive.js` 一直在用**（stores/progress.js 的掌握度模型）；**`sudoku.js` 自 `fd30bc4` 起在用**（SudokuView + check-content 的三档唯一解引擎）。仅 generator/wordproblem 两个死。 |
| "math `src/views/*` 未引用" | **`src/views/HomeView.vue` 在用**：路由 `/` 的目标。旧 7 个 views 已在 Round1 `a114700` 删除。 |
| "literacy `HomeMap/Books.vue` 等死代码" | 已在 Round1 `6bbf99e` 删除（HomeMap.vue、CharacterLearn.vue）。**当前 literacy src 无死文件**。 |
| "数独/应用题/生成器各两套实现" | 数独已收敛（`fd30bc4` 保留 core/engine/sudoku.js、删除 utils/sudoku4.js）；应用题与生成器仍双套，见下表。 |

## 决策表

### math-app 删除清单（5 个死文件，共 389 行，全部零入边，已在含 fd30bc4 的树上复验）

| 文件 | 行数 | 决策 | 理由 |
| --- | --- | --- | --- |
| `src/core/engine/generator.js` | 129 | **删除** | randInt/shuffle/distractors 已被在用的 `utils/random.js`（numericOptions 含错因偏移）覆盖；其「题目协议」设计已由 QuizShell（625 行，`fd30bc4`）+ `data/errorTags.js` 以更完整形态落地。 |
| `src/core/engine/wordproblem.js` | 44 | **删除** | 模板实例化（参数采样+皮肤填充）被在用 `data/wordProblems.js` 的 make() 闭包模式取代，后者现已扩至 34 类母题，含 hint/equation/unit/visual 字段。 |
| `src/core/canvas/stage.js` | 66 | **删除** | Canvas 渲染基座，无任何 canvas 玩法引用；Round2 P0 不含七巧板/迷宫。需要时 `git show 9f8904d:apps/math-app/src/core/canvas/stage.js` 恢复。 |
| `src/data/word-problems.js` | 76 | **删除** | 4 母题骨架（WP_TEMPLATES），是在用 `data/wordProblems.js`（34 母题、WORD_PROBLEMS）的真子集且字段更弱。两文件仅差一个连字符，删错即致命——**删带连字符的那个**。 |
| `src/composables/usePointerDrag.js` | 74 | **删除** | 全仓无引用；当前所有玩法均为点选/键盘交互，无拖拽。 |

### math-app 保留项（曾被怀疑或曾在 v1 列删，经查在用）

| 文件 | 状态 |
| --- | --- |
| `src/core/engine/adaptive.js` | 保留。stores/progress.js 引用（掌握度模型）。 |
| `src/core/engine/sudoku.js` | **保留（v1 曾列删，v2 反转）**。`fd30bc4` 将数独收敛到此引擎：4/6/9 三档、唯一解校验、生成耗时上限已进 check-content。`utils/sudoku4.js` 已被该提交删除，无需再动。 |
| `src/core/audio/sound.js` | 保留。全部视图引用。Round2 P1 的 Tone→WebAudio 瘦身应**保 API 换实现**，不动调用方。 |
| `src/utils/sound.js` | 保留。门面（统一静音开关），非重复实现。 |
| `src/views/HomeView.vue` | 保留。路由 `/` 目标。 |

### math-app 配套修改（与删除同一提交）

1. `README.md`（math）提及 `usePointerDrag` 的句子——删掉。
2. `src/data/curriculum.js` 注释 `M6 应用题(引用 word-problems.js 模板)` → 改为 `wordProblems.js`；
   四个技能点的 `params: { template: 'combine'|'remain'|'diff'|'times' }` 指向已删模板 id 且**全仓无消费方**（已核实），
   直接删除这四处 `params.template`，避免误导后续代理。

### literacy-app（无删除动作）

| 文件 | 决策 | 理由 |
| --- | --- | --- |
| `src/utils/srs.js` | **保留（重点）** | 应用侧零引用，但被 `scripts/test-srs.mjs` 测试覆盖（`9f8904d` 刚扩了用例），且是 P0#2「FSRS 接线」的目标文件（另一代理正在 literacy-fsrs 分支推进）。**不是死代码，是待接线资产。** |
| `src/utils/sfx.js` / `speech.js` | 保留不动 | 21 行门面包装 `utils/audio.js`。views 走门面、App/components 直连 audio.js 的路径不一致属 P2 美化，且并发代理正在改 audio.js，本轮**不动**以避冲突。 |
| 其余 src 文件 | 保留 | 全部在引用图内（10 视图入路由、组件/数据/store 全有入边、theme.css 经 base.css @import）。 |

### 跨 App 重复（本轮不合并）

MascotCompanion vs MascotBot、StarBurst vs StarField、两套 progress store、两套音效栈——
形似但业务语义已分叉，抽到 shared/ 的收益低于回归风险。Round2 仅按 P0#3 做设计令牌迁移
（literacy theme.css → shared/design-tokens.css），组件级共享留给 Round3 评估。

## 归并执行顺序（opus-fast 按序执行）

**步骤 0 — 守卫（必做）**

```bash
cd /workspace
git branch --show-current   # 确认所在分支正确、且历史含 fd30bc4
git log --oneline -5
rg -n "core/engine/(generator|wordproblem)|core/canvas|word-problems\.js|usePointerDrag" \
   apps --glob '!**/dist/**' --glob '!**/node_modules/**'
```

期望：只命中待删文件自身、README.md 与 curriculum.js 的注释、`.agent_workspace/` 历史文档。
若命中任何 **新的 src/scripts 引用**（说明并发代理接了这些文件），立即中止并重估。
若树上已不存在某待删文件（被并发代理处理），跳过该文件即可，不要恢复。

**步骤 1 — 纯删除（一个提交，零功能风险）**

```bash
git rm apps/math-app/src/core/engine/generator.js \
       apps/math-app/src/core/engine/wordproblem.js \
       apps/math-app/src/core/canvas/stage.js \
       apps/math-app/src/data/word-problems.js \
       apps/math-app/src/composables/usePointerDrag.js
```

同提交内完成配套修改（README、curriculum.js 注释与 params.template）。
提交信息建议：`chore(math): 删除零引用的并行开发遗留实现（generator/wordproblem/canvas/旧母题库/拖拽composable）`。
**只 add 上述 7 个文件路径。**

**步骤 2 — 验证后立即 push**

```bash
cd apps/math-app && npm run check:content && npm run build && npm run smoke
cd /workspace && git push -u origin <当前分支>
```

check:content 经 register-alias.mjs 直接以 Node 加载 src（不走 Vite），能兜住脚本层断链
（注意它现在 import `core/engine/sudoku.js`，勿删该引擎）；build + smoke 兜住应用层断链。
任一失败先查是否并发代理改动所致，勿盲目回滚他人文件。

**步骤 3 — literacy 无归并动作。** FSRS 接线属 P0#2 独立任务（literacy-fsrs 分支在做），不在本计划内。

## 风险清单（按严重度排序）

1. **并发写树竞态**：其他代理会切分支、提交、甚至反向收敛（数独一例：v1 计划删 engine 保 utils，
   `fd30bc4` 实际删 utils 保 engine）。缓解：步骤 0 守卫必做、删除到 push 的窗口压到最短、
   只 add 白名单路径、执行基准必须含 `fd30bc4`。
2. **同名陷阱**：`word-problems.js`（删）与 `wordProblems.js`（保）只差连字符。逐一核对 `git rm` 路径。
3. **简报/旧计划失真导致超删**：adaptive.js、**core/engine/sudoku.js**、views/HomeView.vue、
   utils/sound.js 均在用，已列入保留表，不得删除。
4. **check-content.mjs 以相对路径直连 src**：它不经打包器，Vite build 通过不代表脚本没断，两条验证都要跑。
5. **文档诱导复活**：`.agent_workspace/math-architecture.md` 仍描述完整 engine 层架构。本文声明：
   题目协议以 QuizShell + errorTags.js 实现为准，generator/wordproblem/stage 删除后勿按旧文档重建；
   需要历史原文时用 `git show 9f8904d:<path>`。
6. **分支拓扑混乱**：本计划 v1 提交（65b0518）已被卷入 quizshell 分支历史；v2 同步推送至
   `cursor/hongen-edu-apps-9f67`。父代理合并各分支时，本文件以**内容最新者为准**（v2）。
