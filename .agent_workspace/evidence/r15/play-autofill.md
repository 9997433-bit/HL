# Round 15 · H5 全库自动补齐（缺了自动补）

分支：`cursor/r15-play-autofill-9f67`
（先从 `cursor/r15-orchestration-9f67` @ 5940319 起，两次合入编排分支，最后一次 @ d77de00）
Model slug：claude-opus-5-thinking-high-fast

## 这一轮最后落下的是什么

本分支第一版自己铺了一层「富脚本 → 生成层 → 现算」的解析（并顺手翻译了富脚本道具），
先前那版已被编排分支上的 H2「三套剧本方言归一到六种互动」整块覆盖——归一层做的是同一
件事而且做得更完整（19 种模板 → 6 种渲染器，道具翻译在 `toStage()` 里统一做）。
合入时把 `char-play.js` / `char-play-templates.js` / 生成器整块让给上游，只留下两处：

1. **生成器不再把富脚本烤进生成物**，`PLAY_ROWS` 给全部 1820 字留一行地板
2. **`check:data` 补四条数据层门槛** + `npm run verify:char-play`

## 1. 为什么地板要铺满 1820 行

运行时读富脚本是 `char-play.js` 直接 `import` `char-play-rich.js`，生成物里的
`RICH_PLAYS` 没有任何人读。而上游生成器把这 272 个字**从 `PLAY_ROWS` 里挖掉**、
另存成一份 JSON 副本，于是：

- 富脚本改一条模板、撤一条，那个字就掉到「字表外生僻字」那层（`source: 'runtime'`），
  拿不到课文线索句，玩法也从主题轮转里重挑——地板破了一个洞，没有任何门槛看得见
- 生成器认得的模板比引擎少 8 种，重跑时会把富脚本的 `swipe-motion` / `sound-tap` /
  `sort-buckets` 按主题重挑一遍（跑一次就是 9 条 `! 富脚本「扫」的模板…不认识` 警告）
- 编排分支上的生成物是富脚本落地之前生成的，`--check` 已经对不上（红）

改成「地板铺满、富脚本只点个数」之后：数据行与编排分支 @ d77de00 committed 的**逐字节
一致**（diff 只有文件头那两行和 `RICH_PLAYS` 这个死导出），生成器重新幂等。

```
$ npm run gen:char-play
Play 场景已生成：1820 字全覆盖（带字义线索 1818，其中 272 字另有手写富脚本盖在上面）。
  主题 24 类：plant 187，hand 160，person 140，number 132，tool 113，mouth 107，water 103，home 95
  模板 11 种：emoji-hunt 339，word-build 337，tap-reveal 276，pair-match 236，scene-tap 229，…

$ npm run verify:char-play
✓ char-play-generated.js 是最新的（1820 字）

$ git diff origin/cursor/r15-orchestration-9f67 -- src/data/char-play-generated.js
 1 file changed, 5 insertions(+), 8 deletions(-)      ← 1820 行数据一行没动
```

## 2. `check:data` 的四条

`test:play` 逐字验道具玩不玩得完；这四条守的是数据层，破了孩子会点开一张
「和别的字长得一样」的卡片，而探针仍然是绿的：

```
$ npm run check:data
  ✓ Play 补齐索引覆盖全库 1820/1820          ← 字表里的字全部落在 rich / generated 两层
  ✓ Play 旁白一字一句：1820/1820 条不重样（要求 ≥ 95%）
  ✓ 字表外的字也有兜底 Play，且标了 templateFallback   ← getCharPlay('龘') → runtime
  ✓ Play 补齐索引与生成器一致                ← 内部跑一次 gen --check，字表改了没重跑就红
内容自检：84 项通过，0 项失败。
```

## 契约现状（合入后）

| 层 | 文件 | `source` / `templateFallback` | 覆盖 |
|---|---|---|---|
| 富脚本 | `src/data/char-play-rich.js` | `rich` / `false` | 272 |
| 补齐索引 | `src/data/char-play-generated.js`（本岗生成） | `generated` / `true` | 1820 行地板，实际生效 1548 |
| 现算 | `char-play.js` 的 `generatedPlay()` 尾巴 | `runtime` / `true` | 字表外的生字 |
| 兜底 | `char-play.js` 的 `emergencyPlay()` | `emergency` / `true` | 上面全炸时 |

`getCharPlay(char)` **永不返回 null**：`getCharPlay('')`、`getCharPlay(null)` 退到「字」，
字表外的「龘」拿到 `emoji-hunt` / `pick`。

## 实测（`/tmp/wt-r15-autofill`，node v22）

```
$ node -e "CHARACTERS.every(c => getCharPlay(c.char)?.template)"
CHARACTERS 1820 · every template true · every kind ok true · holes 0
source {"rich":272,"generated":1548} · distinct narration 1820/1820

$ npm run test:play
char-play 自测：1820 字，模板 19 种 / 互动 6 种
  来源：generated 1548 / rich 272（模板补齐 1548 字，空洞 0）
✓ 全库每个字都有玩得完的场景

$ npm run build && npm run check:bundle
  ✓ 首屏 JS 325 KB（预算 420 KB）        ← 与编排分支持平，补齐索引不进首屏
构建产物体检：4 项通过，0 项失败。
CharDetailView-*.js 253.6 KB（按需，随「玩」步下载）

$ npm run check:round15   （仓库根）
Round 15 check (ROUND15-v1.1): 7/8    ← 仅 H8 红：worktree 里没有 android:sim 产的双 APK
  ✓ H5 自动补齐管道就位（apps/literacy-app/scripts/gen-char-play.mjs，fallback 条目已打标）

$ node scripts/smoke.mjs
共 164 条路由 + 45 项交互，0 项有问题。
```

## 顺手查清的一件事（不是本分支引入的）

上一轮 smoke 里 `ROUND14_H5：L1 字卡单字与例句优先请求随包离线范读` 红过一次。
用同一份探针分别跑编排分支 @ 89d2546 和本分支的 `dist`，两边都停在
`{"phase":"play","tts":"offline-l1"}`——五步重映射之后单字页从「玩」起步，
`.intro__say` 8 秒内不在 DOM 里，与补齐索引无关。编排分支已在
`a27f287 test(literacy): keep offline TTS smoke phase-aware` 修好，本分支合了进来。

## 重跑

```
cd apps/literacy-app
npm run gen:char-play      # 字表 / 课文 / 字源 / 富脚本 改了都要重跑
npm run verify:char-play   # 只校验是不是最新（check:data 里也会跑一遍）
```
