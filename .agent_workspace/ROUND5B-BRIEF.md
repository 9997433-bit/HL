# Round 5B 简报 · Play Layer（UI/玩法超越）

> 基线：`cursor/openmoji-integration-9f67` @ Round 5 闭合（`check:round5` 12/12）
> 集成分支：`cursor/openmoji-integration-9f67`
> 门禁：`npm test` 全绿 → `npm run check:round5b` → `npm run test:round3`

## 目标

让孩子**觉得好玩、爱玩**——「玩的同时把东西学了」。工程/a11y 已领先，本轮回补**情感层与微反馈**，对标 Duolingo / WildReader 等高星项目的「每日动机 + 吉祥物陪跑 + 即时正反馈」。

## P0 必交付（6 项硬门槛）

| # | 能力 | 验收 |
|---|---|---|
| P1 | **每日冒险 3 件事** | 识字首页展示今日 3 项可勾选任务（学新字/复习/绘本或成语/小游戏），完成有庆祝 |
| P2 | **吉祥物全程陪跑** | 墨墨/数学吉祥物在 ≥5 条核心路由常驻（非仅弹窗），可点触语音/鼓励 |
| P3 | **统一 `useFeedback`** | 识字+数学共用微反馈 composable（星星粒子/震动降级/音效钩子），Quiz/游戏/写字至少各接 1 处 |
| P4 | **地图叙事解锁** | 识字单元地图或数学星球地图：未解锁灰显+一句话剧情；解锁有过渡动画 |
| P5 | **游戏大厅街机化** | `GamesView` 卡片网格+街机风标题/霓虹边；每款游戏有「一句话玩法」 |
| P6 | **答对音效节奏** | 连对 streak 音高递进或节拍强化；两 App 各 ≥1 条答题链路接线 |

## 子代理分工（10）

| # | 模型 | 分支 | 任务 |
|---|---|---|---|
| 1 | fable | `cursor/r5b-arch-contracts-9f67` | Play Layer 架构契约（组件边界、stores、路由） |
| 2 | fable | `cursor/r5b-module-audit-9f67` | 洪恩玩法/UI 对标审计（好玩度差距表） |
| 3 | fable | `cursor/r5b-acceptance-spec-9f67` | ROUND5B-ACCEPTANCE + check-round5b + acceptance-log |
| 4 | opus-fast | `cursor/r5b-daily-adventure-9f67` | 识字每日冒险 3 任务 + 进度持久化 |
| 5 | opus-fast | `cursor/r5b-mascot-companion-9f67` | 吉祥物全程陪跑（识字墨墨 + 数学 MascotBot 扩面） |
| 6 | opus-fast | `cursor/r5b-use-feedback-9f67` | `useFeedback` composable + 双 App 接线 |
| 7 | opus-fast | `cursor/r5b-map-narrative-9f67` | 地图/星球叙事解锁与过渡 |
| 8 | opus-fast | `cursor/r5b-games-arcade-9f67` | 游戏大厅街机化 UI |
| 9 | gpt-sol | `cursor/r5b-sfx-rhythm-9f67` | 答对音效节奏 + streak 反馈 |
| 10 | gpt-sol | `cursor/r5b-regression-gate-9f67` | check:round5b + test:round3 + Lighthouse 回归 |

## 规则

- 分支 `cursor/<name>-9f67`；首行声明 Model slug
- 不破坏 Round 5 内容门禁；合并前 `npm run check:round5` 仍全绿
- reduced-motion / 庆祝可跳过必须保留
- 参考：duolingo-clone、WildReader、robis-design-best-practice skill
