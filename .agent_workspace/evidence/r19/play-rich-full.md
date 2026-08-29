# Round 19 H2 · 全库富 Play 1820 条

分支 `cursor/r19-play-rich-full-9f67`（基于 `origin/cursor/r19-orchestration-9f67`）。

## 计数前后

| 口径 | 之前（Round 18） | 之后（Round 19） |
| --- | --- | --- |
| seed 脚本行 | 1240（u1–u70） | **1820**（u1–u99） |
| `countRichPlays()` | 1240 | **1820** |
| narration 全库去重 | 1240 | **1820** |
| 模板回填 | 580（u71–u99） | **0** |
| 生成期门槛 `MIN_RICH_PLAYS` | 1200 | 1820 |
| 生成期门槛 `MIN_DISTINCT_NARRATION` | 960 | 1600 |
| `RICH_UNIT_LIMIT` | 70 | **99** |

新写的 580 条覆盖 u71–u99（识字山洞 → 识字终点）：每条对照 `chars/uN.js` 字义写玩法与旁白——
纫是穿针、坝是拦水、吠是狗叫、钓是甩钩、茧是结壳、莫是停在线内。
旁白 ≤24 字，全库 `narrationKey()` 归一后与旧 1240 句零撞句。

## 复跑命令与输出

```
$ npm run gen:play:rich --workspace=apps/literacy-app
[play-rich] 1820 条富脚本，覆盖 99 个单元（u1–u99）。
[play-rich] 分片 99 片共 548 KB，平均每片 6 KB；manifest 9 KB（同步路径上只有它）。
[play-rich] 模板分布：count-tap 157、swipe-motion 268、morph-story 68、sound-tap 109、
grow-tap 169、emoji-hunt 121、tap-reveal 145、drag-parts 133、trace-path 114、scene-poke 113、
sort-buckets 112、pair-match 98、pop-bubbles 91、rain-catch 46、word-build 8、color-fill 68

$ npm run check:play:rich --workspace=apps/literacy-app
[play-rich] seed 校验通过：1820 条，覆盖 99 个单元、16 个模板，旁白 1820 句不重样。

$ npm run test:play:guard --workspace=apps/literacy-app
真 seed：1820 条 / 99 个单元 / 旁白 1820 句不重样
运行时：ROUND17_H2 · 1820 条 / 旁白 1820 句不重样
✓ 撞句与条数不足都在生成期被拦下，真 seed 达线

$ npm run test:play --workspace=apps/literacy-app
来源：rich 1820（模板补齐 0 字，空洞 0）
✓ 全库每个字都有玩得完的场景
```

运行时抽查（`loadAllRichPlays()` 后）：

| 字段 | 值 |
| --- | --- |
| `countRichPlays()` / `richPlayCoverage().plays` | 1820 |
| `richPlayCoverage().narrations` | 1820 |
| `RICH_PLAY_MANIFEST.plays` | 1820 |
| `RICH_PLAY_UNITS.length` | 99 |
| `RICH_PLAY_PROBE_ROUND19` | `ROUND19_H2` |
| `templateFallback === false` | 1820 / 1820 |

## ROUND19_H2 标记

剥掉注释后仍读得到（和 `check-roundN.mjs` 的 `scanExecMarker` 同一套 strip 规则）：

- `apps/literacy-app/scripts/gen-char-play-rich.mjs` — `const PROBE_MARK_R19 = 'ROUND19_H2'`
- `apps/literacy-app/src/data/play-rich/index.js` — `export const RICH_PLAY_PROBE_ROUND19 = 'ROUND19_H2'`
  以及 `RICH_PLAY_PROBE_HISTORY`（含 ROUND15–19）
- `apps/literacy-app/scripts/test-play-rich-guard.mjs` — 断言生成器与 manifest 都带着 `ROUND19_H2`，
  往轮 `ROUND18_H2` 仍在；门槛抬到 1820 / 1600

## 边界

- 舞台精美度（H3）与剖析播放器（H4）不在这一支；这里只动 seed、生成器门槛、分片生成物与 guard。
- 分片仍按单元懒加载：`play-rich/uN.js` + 轻量 `index.js` manifest，同步路径不背旁白/道具。
