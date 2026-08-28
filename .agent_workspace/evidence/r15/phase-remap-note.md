# R15 · 五步重映射（玩→认→练→写→说）实测记录

分支：`cursor/r15-phase-remap-9f67`（自 `cursor/r15-orchestration-9f67`）
Model slug: claude-opus-5-thinking-high-fast

## PHASES 最终定义

| 序 | id | label（步骤条） | full（面板/播报） | emoji | 记账 |
|---|---|---|---|---|---|
| 1 | `play` | 玩 | 玩一玩 | 🎮 | 否（暖场，随时「先不玩了」） |
| 2 | `intro` | 认 | 认一认 | 👀 | 是 |
| 3 | `listen` | 练 | 练一练 | 👂 | 是 |
| 4 | `trace` | 写 | 写一写 | ✍️ | 是 |
| 5 | `speak` | 说 | 说一说 | 🗣️ | 是 |

默认 `phase = 'play'`。原第 5 步「领奖励」并入「说」：答完题星星就在同一块面板里
开出来（`.ask + .reward`），不再单开一屏。`progress.completeCharFlow()` 仍只在
认/练/写四步 + 说都真的做完时才调用，跳步不伪造 `done`。

## 自动衔接

| 触发 | 去向 | 延时 |
|---|---|---|
| 玩满一轮 / 玩步空闲 22s | 认 | 1.4s / 0.6s |
| 字源动画演完 | 练 | 0.9s |
| 听一次读音 / 认步空闲 18s | 练 | 1.6s / 0.6s |
| 练答对或两次后揭晓 | 写 | 1.4s / 2.0s |
| 描红写完 / 跳过描红 | 说 | 1.4s / 0.9s |
| 说答完 | 就地开奖（不换步） | 0 |

每次自动衔接照旧先挂 `pendingNext`，屏幕上有「✋ 等一下」可按停，读屏先播报下一步。

## 实测（headless Chrome，dist 生产包）

```
rail = play(玩) → intro(认) → listen(练) → trace(写) → speak(说)
默认 phase = play
玩：☀️ 藏在画面里啦，找出跟「日」是一伙的。
玩完预告 = 马上进入「认一认」… ✋ 等一下
→ phase = intro
认：字源舞台已默认挂载并 ready（未点任何「来历」按钮）
→ phase = listen
→ phase = trace
→ phase = speak
说：就地开奖 → {"flows":1,"traced":1,
  "steps":["play","intro","listen","trace","speak"],
  "reward":"⭐ 这一趟 +7 星 🧭 「日」完整学过 1 遍 🏆 已掌握 🎖️ 新徽章到手！ 🌱 启蒙芽 …"}
换字「们」玩法：👥 会慢慢变成「们」，点一下往下看。
减少动态：玩→认→练→写 全程可走
控制台错误：无
```

截图：`phase-1-play.png` / `phase-2-intro-etymology.png` / `phase-3-listen.png` /
`phase-4-trace.png` / `phase-5-speak-reward.png`（430×960 @2x）。

## 门禁

`node scripts/check-round15.mjs` → **4/8**：H1 / H2 / H4 / H7 绿。
H3（富脚本 ≥200）、H5（gen-char-play 管道）、H6（写步引导）属其它子代理；
H8 在本 worktree 红是因为 round13 H6 依赖未入库的 APK/日志构建产物
（`/workspace` 同一份探针跑 7/8），与本次改动无关。

## 与 play-engine 分支的关系

`src/data/char-play.js` 与 `src/components/CharPlayStage.vue` 是**薄壳**：
前者只保证 `getCharPlay()` 对任何字都给得出 `template`（全库 1820/1820），
后者只做「点满道具就算玩过一轮 + 随时可跳过 + 减少动态下不建时间线」。
play-engine 到位后以 engine 为准替换，`getCharPlay` 契约与
`CharPlayStage` 的 `char` prop / `done`·`skip` 事件保持不变。
