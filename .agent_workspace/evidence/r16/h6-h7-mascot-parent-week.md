# R16 · H6 学伴人格 + H7 家长可解释周报

> 分支 `cursor/r16-mascot-parent-week-9f67`（基线 `cursor/r16-orchestration-9f67`）
> 探针原话（`node scripts/check-round16.mjs --json`）：
>
> ```json
> {"id":"H6","status":"pass","msg":"H6 学伴人格台词充足（标记=true）"}
> {"id":"H7","status":"pass","msg":"H7 家长可解释周报就位"}
> ```

## H6 学伴人格剧本

台词从「一页一组常驻鼓励语」拆成两层：**场景**按路由走，**阶段**按孩子此刻的状态走。
阶段这一层是墨墨/小算「有人格」的地方——它先判断现在最该说哪一类话，再从那一类里轮着说。

| App | 阶段 | 条数 |
|---|---|---|
| 识字（墨墨） | 久别重逢 / 该歇歇了 / 刚掌握 / 连着答对 / 答错了 / 要复习 / 今天够了 / 要学新字 / 随便聊聊 | **41** |
| 数学（小算） | 久别重逢 / 该歇歇了 / 连着答对 / 错题欠账 / 算错了 / 今日冒险 / 今天够了 / 随便聊聊 | **33** |

合计 74 条，识字单侧已过 ≥40 的门槛（`countMascotStageLines()` 是运行时计数，不是数源码里的引号）。

- 标记 `ROUND16_H6` 落在可执行代码：`export const ROUND16_H6_STAGE_SCRIPT = 'ROUND16_H6'`，
  由 `pickMascotStage()` 随判定结果一起返回。
- 阶段数组的顺序就是优先级：孩子坐了 20 分钟还在硬撑时，「该歇歇了」压过「还有 3 个字要复习」。
- 台词一律不含 emoji（回归里有断言）——这些句子直接交给 SpeechSynthesis，
  表情符号有的读成「笑脸」，有的直接卡住。

接线：

- `useMascotCoach(scene)` 自己从 store 取阶段所需的上下文：到期数、今天新认几个字、
  本次会话坐了多久、护眼提醒是否已触发、距上次真正学过隔了几天。
- 答题页才知道的东西（连对几个、这一下错没错、题面是哪个字）走第二个参数传入：
  `useMascotCoach('games', { combo, recentWrong, char })`。
  已在识字《听音识字》接上——那是全 App 唯一有「连对」计数的地方，
  墨墨现在会在连对 3 个之后换到夸奖那组、答错之后先安慰。
- 旧写法 `useMascotCoach('home')` 一字未改仍然工作，11 处调用点无需跟改。

## H7 家长可解释周报

家长中心原来能回答「练了多少、错在哪」，回答不了「所以这周该练什么」。周报补的就是这一句。

位置：

- 识字：`/parent` → **总览之后、徽章墙之前**的「🗞️ 本周一句话」卡片
  （`apps/literacy-app/src/views/ParentView.vue`，`[data-weekly-report]`）
- 数学：`/parent` → **总览之后、显示主题之前**的同名面板
  （`apps/math-app/src/modules/parent/ParentView.vue`，`[data-weekly-report]`）

算法：

- 纯函数住在 `apps/*/src/utils/weeklyReport.js`，不 import Vue、不读 store，
  Node 探针与回归可以直接跑；`composables/useWeeklyReport.js` 只负责喂数据。
- 标记 `ROUND16_H7` 落在可执行代码：`export const ROUND16_H7_WEEKLY_REPORT = 'ROUND16_H7'`，
  随每份报告一起返回（`report.script`）。
- **只挑一个弱项**是刻意的：列五条家长一条也不会做。判定表按优先级排，第一条命中的即弱项。

| App | 弱项规则（按优先级） |
|---|---|
| 识字 | 这周没怎么练 → 来的天数太少 → 复习欠账 → 错字扎堆 → 记不牢 → 只认不写 → 缺少输出 → 状态不错 |
| 数学 | 这周没怎么练 → 来的天数太少 → 错题欠账 → 同一类错因反复出现 → 正确率偏低 → 技能点卡住 → 玩得太偏 → 状态不错 |

- 建议练习恒定 1–3 条，每条都有标题、「凭什么推荐它」和一个可以直接点过去的落点
  （识字落到 `/learn/字`、`/listen`、`/books`…；数学落到星球路由、`/daily`、`/progress`…）。
- 条件式建议在极端存档下会不够，补了两条恒成立的兜底——家长只看到孤零零一行会以为没算出来。
- 全部本机现算：不联网，也没有拿别的孩子做对比。卡片底部直接对家长说明了这一点。

## 回归

`npm run test:mascot`（已挂进 `npm test`，见 `scripts/test-mascot-weekly.mjs`）：
17 项全绿，逐条输出见同目录 `h6-h7-test-output.txt`。

断言压的是结构不是措辞（台词与建议的说法会一直改）：

- H6：每个阶段在空上下文下也有话说、判定优先级逐条对齐、台词不夹 emoji、
  场景名写错仍有台词、阶段台词排在场景台词前面。
- H7：两个 App 各 8 条弱项规则全部命中一遍；建议练习 1–3 条、id 不重复、
  每条都有 `why` 和以 `/` 开头的落点；空输入也能出一份完整报告。

## 未覆盖 / 交接

- 识字单字页（`CharDetailView.vue`）没有接 `{ combo, recentWrong }`：那一页正被 H2
  的子代理改，避免撞车。接口已经留好，接线只需在调用处补第二个参数。
- 数学答题壳（`QuizShell`）同理未接 `recentWrong`；`combo` 本来就在 store 里，
  小算已经能读到，所以「连对」那组台词在数学侧不接也会出。
- 本地环境 `check:round15` 停在 7/8，红的是 H8（依赖 `npm run android:sim` 重建双 APK），
  与本分支无关；识字 smoke 唯一一条红是 `public/ocr/` 未生成（`npm run gen:ocr`），同为环境问题。
