# Round 19 · H3 玩关精美度（CharPlayStage）

分支：`cursor/r19-play-polish-9f67`（基线 `origin/cursor/r19-orchestration-9f67`）
探针：可执行 `ROUND19_H3`（剥注释后仍在源码里）
门槛：≥3 类可感知升级 + reduced-motion / 跳过可用 + 不改模板通关判定
契约：`.agent_workspace/round19-architecture.md` §2

## 结论

| 项 | 结果 |
|---|---|
| 可执行标记 `ROUND19_H3` | ✅ `usePlayPolish.js` 导出 + Stage `data-polish` / `POLISH_*` 钩子 |
| ① 多拍节 timeline | ✅ `playMultiBeatTimeline()` + `POLISH_BEATS`：氛围 → 标题 → 主体 |
| ② 道具命中反馈增强 | ✅ `playPropHitFeedback()` + `POLISH_HIT`：涟漪环 + 火花 + 轻弹 |
| ③ 主题氛围层 | ✅ `.play__atmosphere` + `POLISH_AMBIENCE`：主题色光斑 + emoji 微粒 |
| reduced-motion / 跳过 | ✅ 不建 timeline；微粒停飘；「跳过这一步」仍 complete(skipped) |
| 通关判定 | ✅ `taken/need/filled/pushes` 阈值未改 |

## 落点

| 文件 | 作用 |
|---|---|
| `apps/literacy-app/src/composables/usePlayPolish.js` | `ROUND19_H3` / `PLAY_POLISH` + 三件套 API |
| `apps/literacy-app/src/components/CharPlayStage.vue` | 氛围层、入场拍节、命中涟漪、`POLISH_BEATS/HIT/AMBIENCE` DOM |

## 实测

```
$ node apps/literacy-app/scripts/test-play-polish.mjs --require-ready
✓ ROUND19_H3 PASSED: CharPlayStage exposes 3 polish upgrades with reduced-motion

$ node scripts/check-round19.mjs
✓ H3 精美度升级就位（升级词证 3/3，reduced-motion 降级，可执行标记 ×2）
```

（同跑 `check:round19` 其余项仍由 H2/H5/H6/H7/H8 岗交付，本岗只绿 H3。）

## 降级契约

- `settings.reduceMotion` **或** `prefers-reduced-motion: reduce` → `play--static`
- 入场：`data-polish-beats` 标 skipped，三拍瞬时就位
- 氛围：光斑保留、微粒停动画
- 命中：瞬时 outline，不插涟漪 DOM
- catch 雨落 / push 位移等原有降级不变
