# Round 5B 验收标准 —— Play Layer（UI/玩法超越）

> 版本：Round 5B v1.0（2026-08-27）
> 依据：`.agent_workspace/ROUND5B-BRIEF.md` + `.agent_workspace/SURPASS-HONGEN-MASTER-PLAN.md`
> 配套：`.agent_workspace/acceptance-log-round5b.md`（实测回填模板）、`scripts/check-round5b.mjs`（P1–P6 机读探针）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
| --- | --- | --- | --- |
| G1 | 全量单测回归 | `npm test` | 全绿；Round 5B 改动不得回归 Round 5 成果 |
| G2 | Round 5 内容不退化 | `npm run check:round5` | 退出码 0（12/12 保持全绿） |
| G3 | Round 5B Play 硬门槛 | `npm run check:round5b` | 退出码 0（P1–P6 全绿，见 §1；基线 3cf37eb 为 **0/6 有意红灯**，见 §4） |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；Lighthouse Perf/A11y ≥ 90；axe critical/serious = 0 |
| G5 | 出包 + 总达成率 | `npm run build:all` + acceptance-log | zip 体积回填 §log；P0 达成率 ≥ **95%**，日志无「待回填」残留 |

---

## 1. 六项 Play 硬门槛（P1–P6）

`npm run check:round5b` 逐项断言，任一 FAIL 即退出码 1。`--json` 输出机读汇总（`passed`/`failed`/`results`）供编排器聚合。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
| --- | --- | --- | --- | --- |
| P1 | 每日冒险 3 件事 | ① 任务模板池 ≥ **3**（学新字/复习/绘本或成语/小游戏轮换）；② 每日摆出 ≥ **3** 件（`DAILY_TASK_COUNT ≥ 3`）；③ 有完成态且可手动勾选；④ 识字 `HomeView` 接线入口；⑤ 完成有庆祝 | 探针 §2.1 + 实机走查 §3 | r5b-daily-adventure |
| P2 | 吉祥物全程陪跑 | 识字 `MascotCompanion` 与数学 `MascotBot` 组件存在；**路由级视图**（非 App.vue 弹窗）接线：识字 `views/*.vue` ≥ **5** 且数学 `modules/**` 视图 ≥ **5**；可点触语音/鼓励 | 探针 §2.2 + 实机走查 §3 | r5b-mascot-companion |
| P3 | 统一 `useFeedback` | ① 统一 composable（`shared/composables/useFeedback.js` 或双 App 各一份同 API）；② 能力齐备：星星粒子 + **震动降级（vibrate）** + 音效钩子；③ 三个面各接 ≥1 处：数学 `QuizShell`、识字小游戏视图、识字写字链路 | 探针 §2.3 + 实机走查 §3 | r5b-use-feedback |
| P4 | 地图叙事解锁 | 剧情注册表 ≥ **5** 条（每条一句话 `story`）且地图视图接线 + 解锁过渡标记；识字单元地图**或**数学星球地图任一达标即过；未解锁灰显保持 | 探针 §2.4 + 实机走查 §3 | r5b-map-narrative |
| P5 | 游戏大厅街机化 | ① `GamesView` 街机风（`arcade`/街机 标记 + 卡片网格 + 霓虹边）；② `data/games.js` 注册表每条 `route` 都渲染进大厅；③ 每款游戏有一句话玩法（`howToPlay`/`tagline`） | 探针 §2.5 + 实机走查 §3 | r5b-games-arcade |
| P6 | 答对音效节奏 | ① 识字 `utils/audio.js|sfx.js` 与数学 `utils/sound.js` 提供 streak 音高递进入口；② 两 App 各 ≥ **1** 条答题链路（utils 之外）调用 `sfx.streak(…)`/`streakCue(…)` | 探针 §2.6 + 实机走查 §3 | r5b-sfx-rhythm |

## 2. 探针约定（机读接线契约）

探针是**纯静态分析**（fs + 正则，不 import 应用代码，无 node_modules 可跑）。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

### 2.1 P1 每日冒险

- 任务库：`apps/literacy-app/src/stores/dailyQuest.js`（或 `src/composables/useDailyQuest.js`）
- 模板池：`TASK_SPECS` / `DAILY_TASKS`（模板有 `title:` 或 `id:`，计数 ≥ 3）；`DAILY_TASK_COUNT = 3`
- 完成态：源码含 `completed`（自动判定 + 手动勾选并存，手动优先）
- 接线：`HomeView.vue` 引用 `DailyAdventure` / `dailyQuest`
- 庆祝：`components/` 下 `*daily*` 组件或任务库含 `celebrat|庆祝|burst|StarBurst|confetti`

### 2.2 P2 吉祥物陪跑

- 组件：`apps/literacy-app/src/components/MascotCompanion.vue`、`apps/math-app/src/components/MascotBot.vue`
- 计数口径：识字 `src/views/*.vue`、数学 `src/modules/**/*.vue` 中引用 `MascotCompanion|MascotBot|useMascotCompanion` 的**视图文件数**，各 ≥ 5
- `App.vue` 全局弹窗**不计入**（「常驻非弹窗」）

### 2.3 P3 统一 useFeedback

- 位置：`shared/composables/useFeedback.js`，或识字/数学各一份 `src/composables/useFeedback.js`（API 对齐）
- 能力探针：源码含 `burst|star|粒子`（星星粒子）、`vibrate`（震动降级）、`sfx|sound`（音效钩子）
- 三面接线：`apps/math-app/src/components/QuizShell.vue`、识字 `views/*Game*View.vue` 任一、识字 `CharDetailView.vue` 或 `components/HanziStrokeBox.vue`，各出现 `useFeedback`

### 2.4 P4 地图叙事

- 识字：`apps/literacy-app/src/data/unitStories.js` 导出 `UNIT_STORIES`（每条 `{ id, story }`，`story:` 计数 ≥ 5），`LearnView.vue` 接线
- 数学：`apps/math-app/src/data/planetStories.js` 导出 `PLANET_STORIES`，`modules/home/HomeView.vue` 接线
- 解锁过渡标记：视图或注册表含 `unlock-anim|unlock-reveal|unlock-transition|unlock-fx|unlockCelebrat*`（class 名或标识符均可）
- 两侧任一全部达标即 PASS；过渡动画的观感与 reduced-motion 降级走 §3 人工走查

### 2.5 P5 街机大厅

- `apps/literacy-app/src/views/GamesView.vue` 含 `arcade`（class）或「街机」
- `apps/literacy-app/src/data/games.js` 的每条 `route:` 字符串必须出现在 `GamesView` 源码中（全部渲染）
- 一句话玩法：`howToPlay:` 或 `tagline:` 字段计数 ≥ 注册表条目数（写在视图局部数组或注册表均可）

### 2.6 P6 答对节奏

- 识字：`utils/audio.js` + `utils/sfx.js` 含 `streak`（谱面：`streakChord`/`sfx.streak`，音高逐级递进）
- 数学：`utils/sound.js` 含 `streakCue` 或 `streak:` 入口
- 接线：两 App 各 ≥1 个 utils 之外的文件调用 `sfx.streak(` 或 `streakCue(`（视图直调或经 `useFeedback.correct({ streak })` 转发均可）

## 3. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
| --- | --- | --- |
| W1 | 每日冒险勾选 | 勾第三件时有庆祝；手动勾/取消都算数；隔天任务轮换 |
| W2 | 吉祥物点触 | 点吉祥物出语音或鼓励文案；不遮挡答题区；`prefers-reduced-motion` 下不乱跳 |
| W3 | useFeedback 观感 | 答对星星粒子 + 震动（支持的设备）；答错抖动克制；reduced-motion 全降级 |
| W4 | 解锁过渡 | 新单元/星球解锁有过渡动画且**可跳过**；未解锁灰显 + 一句话剧情可读 |
| W5 | 街机大厅 | 霓虹边不刺眼（护眼主题下辉光收敛）；每台机器一句话玩法孩子读得完 |
| W6 | 连对节奏 | 连对 3+ 音高明显递进；断连回落；家长面板关音效后全静音 |
| W7 | 硬性红线抽查 | 触控 ≥ 56×56、键盘可达、庆祝可跳过（继承 Round 3/4） |

## 4. 基线红灯记录（有意红灯）

基线 `cursor/openmoji-integration-9f67` @ `3cf37eb`（Round 5 闭合、Play Layer 未动工）实测：

```
✗ P1 每日冒险未达标：任务库缺失（stores/dailyQuest.js）；HomeView 未接线；完成无庆祝
✗ P2 吉祥物陪跑 识字 0/5、数学 6/5
✗ P3 useFeedback 未达标：统一 composable 缺失（shared/ 或双 App）；识字小游戏未接线；写字链路未接线
✗ P4 地图叙事未达标：剧情注册表 识字 0、数学 0 条
✗ P5 街机大厅未达标：无街机风标记；一句话玩法 0/4
✗ P6 答对节奏未达标：识字 sfx 无 streak 谱面；数学 sound 无 streakCue

Round 5B Play 门禁：0/6 通过（失败：P1 P2 P3 P4 P5 P6）→ 退出码 1
```

六项全 FAIL 属**有意红灯**：探针先行、交付点绿（继承 Round 4/5 原则）。数学吉祥物已有 6 视图属基线存量，P2 仍以识字侧 0/5 拦截。

## 5. 不回归红线（继承 Round 3/4/5，抽查即可）

- `npm run check:round5` 保持 12/12（1000 字 / 30 绘本 / 60 成语 / 100+ 母题 / 数形演示 / 小游戏 / 字源）
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）
- 触控 ≥ 56×56、键盘可达、庆祝可跳过、`prefers-reduced-motion` 降级——**Play Layer 新增的粒子/霓虹/过渡全部适用**
- 运行时零第三方域名请求；识字首屏 JS gzip < 250KB，Play 资产不得挤进首屏 chunk

## 6. 回填要求

每条 P1–P6 在 `acceptance-log-round5b.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选）。禁止「应该可以」「理论上通过」。未达标项一律进 log §5 未达标表并写明责任分支与计划，不得静默遗漏。
