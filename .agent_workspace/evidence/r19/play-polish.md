# Round 19 · H3 玩关精美度（CharPlayStage）

分支：`cursor/r19-play-polish-9f67`（基线 `origin/cursor/r19-orchestration-9f67` @ `2624e06`）
探针：可执行 `ROUND19_H3`（剥注释后仍在源码里）
门槛：≥3 类可感知升级 + reduced-motion / 跳过可用 + 不改模板通关判定

## 结论

| 项 | 结果 |
|---|---|
| 可执行标记 `ROUND19_H3` | ✅ `usePlayPolish.js` 导出 + `CharPlayStage.vue` DOM `data-round19-h3` |
| ① 多拍节 timeline | ✅ `playMultiBeatTimeline()`：氛围 → 标题 → 主体，≥3 拍 |
| ② 道具命中反馈增强 | ✅ `playPropHitFeedback()`：涟漪环 + 火花 + 靶子轻弹 |
| ③ 主题氛围层 | ✅ `.play__atmosphere` + 主题色光斑 + 主题 emoji 微粒 |
| reduced-motion / 家长减少动效 | ✅ 不建 GSAP timeline；微粒停飘；命中只留瞬时 outline |
| 跳过 | ✅ 「跳过这一步」仍 emit `complete({ skipped: true })` |
| 通关判定 | ✅ `taken/need/filled/pushes` 与原先一致，未改阈值 |

## 落点

| 文件 | 作用 |
|---|---|
| `apps/literacy-app/src/composables/usePlayPolish.js` | 新增。`ROUND19_H3` / `PLAY_POLISH` + 三件套 API |
| `apps/literacy-app/src/components/CharPlayStage.vue` | 接线：氛围层、入场拍节、命中涟漪、DOM 探针属性 |

## 机读核对（本岗位自测）

```
marker files 2
  apps/literacy-app/src/composables/usePlayPolish.js
  apps/literacy-app/src/components/CharPlayStage.vue
multi-beat OK
hit-feedback OK
atmosphere OK
reduced-motion OK
skip OK
completion logic OK（taken≥need / filled 满 / pushes≥need / skip→complete）
```

`PLAY_POLISH` 键名：`multiBeatTimeline` · `propHitFeedback` · `themeAtmosphere`。

## 降级契约

- `settings.reduceMotion` **或** `prefers-reduced-motion: reduce` → `play--static`
- 入场：`data-polish-beats="skipped"`，三拍直接标完成，元素 `gsap.set` 就位
- 氛围：光斑保留、`.play__atmosphere-mote` 停动画
- 命中：`.is-hit-ok-static` / `.is-hit-bad-static`，不插 DOM 涟漪
- catch 雨落、push 位移等原有降级路径不变

## 不碰

- `getCharPlay` / 富脚本分片 / 六种 kind 的通关条件
- `complete` payload 字段形状
- H2 数据岗的 seed / narration（舞台以本岗 UI 为准）
