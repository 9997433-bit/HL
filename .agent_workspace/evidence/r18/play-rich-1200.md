# Round 18 H2 · 富 Play 抬到 1200 条

分支 `cursor/r18-play-rich-1200-9f67`（基于 `origin/cursor/r18-orchestration-9f67`）。

## 计数前后

| 口径 | 之前（Round 17） | 之后（Round 18） |
| --- | --- | --- |
| seed 脚本行 | 940（u1–u55） | 1240（u1–u70） |
| `countRichPlays()` | 940 | **1240** |
| narration 全库去重 | 940 | **1240** |
| 生成期门槛 `MIN_RICH_PLAYS` | 900 | 1200 |
| 生成期门槛 `MIN_DISTINCT_NARRATION` | 720 | 960 |
| `RICH_UNIT_LIMIT` | 55 | 70 |

新写的 300 条覆盖 u56–u70：科学和宇宙、心情和身体、讲故事，以及识字小路 / 小桥 /
小坡 / 树林 / 山谷 / 溪边 / 草原 / 沙丘 / 海湾 / 礁石 / 码头 / 岛屿这 12 个笔画单元。
每条都照字义写玩法：磁是磁铁吸铁钉、箭是火箭往上射、睁是眼皮慢慢抬、
吸是深吸一口气、驮是骆驼背上装货。

去重是**全库口径**：撞句判定用 `narrationKey()` 归一（去标点、去语气词尾），
新句和旧的 940 句一起进同一张表比，一句都没撞——1240 条脚本对 1240 句旁白。

## 复跑命令与输出

```
$ npm run gen:play:rich --workspace=apps/literacy-app
[play-rich] 1240 条富脚本，覆盖 70 个单元（u1–u70），约 336 KB。
[play-rich] 模板分布：count-tap 130、swipe-motion 195、morph-story 47、sound-tap 57、
grow-tap 105、emoji-hunt 85、tap-reveal 99、drag-parts 96、trace-path 80、scene-poke 80、
sort-buckets 77、pair-match 58、pop-bubbles 62、rain-catch 23、word-build 8、color-fill 38

$ npm run test:play:guard --workspace=apps/literacy-app
真 seed：1240 条 / 70 个单元 / 旁白 1240 句不重样
运行时：ROUND17_H2 · 1240 条 / 旁白 1240 句不重样
✓ 撞句与条数不足都在生成期被拦下，真 seed 达线

$ npm run test:play --workspace=apps/literacy-app
来源：rich 1240 / generated 580（模板补齐 580 字，空洞 0）
✓ 全库每个字都有玩得完的场景

$ node scripts/check-round17.mjs
✓ H2 富 Play 1240 ≥ 900，narration 去重 1240 ≥ 720（可执行标记 ×4）
```

`node --test scripts/test-round17-smoke.mjs` 6/6 通过：运行时 `richPlayCoverage().probe`
仍是 `ROUND17_H2`，往轮探针的口径没被这一轮碰坏。

## ROUND18_H2 标记

剥掉注释后仍读得到（和 `check-roundN.mjs` 的 `scanExecMarker` 同一套 strip 规则）：

- `apps/literacy-app/scripts/gen-char-play-rich.mjs` — `const PROBE_MARK_R18 = 'ROUND18_H2'`
- `apps/literacy-app/src/data/char-play-rich.js` — `export const RICH_PLAY_PROBE_ROUND18 = 'ROUND18_H2'`
  以及 `RICH_PLAY_PROBE_HISTORY`
- `apps/literacy-app/scripts/test-play-rich-guard.mjs` — `const ROUND18_MARK = 'ROUND18_H2'`，
  第 6 段断言生成器和生成物里都还带着它

## 边界

拆包（索引 + 单元分片）不在这一支里，归 Round 18 的另一岗；这里只动 seed、
生成器门槛常量和负例自测，`char-play.js` 一个字没改。
