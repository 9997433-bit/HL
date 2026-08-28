# Round 15 · H5 全库自动补齐（缺了自动补）

分支：`cursor/r15-play-autofill-9f67`（先从 `cursor/r15-orchestration-9f67` @ 5940319 起，
后合入编排分支 @ 89d2546）
Model slug：claude-opus-5-thinking-high-fast

## 三层契约

| 层 | 文件 | 谁写 | `templateFallback` / `source` |
|---|---|---|---|
| 富脚本 | `src/data/char-play-rich.js` | 手写 seed（272 条，u1–u20） | `false` / `rich` |
| **补齐索引** | `src/data/char-play-generated.js` | **`scripts/gen-char-play.mjs`（本轮）** | `true` / `generated` |
| 现算兜底 | `src/data/char-play.js` 的模板运行时 | 引擎 | `true` / `fallback` |

`getCharPlay(char)` 依次取用，**永不返回 null**：字表 1820 字全部落在前两层，
字表外的字（绘本生字、搜索进来的生僻字）落第三层。

## 补齐索引里到底有什么

一行一个字：`汉字|模板|一句话线索`。只存「玩什么 + 说什么」，道具仍由运行时现算，
所以 1820 字压下来 65 KB。

线索句和玩法选择都来自**运行时够不着的语料**，这也是这一层存在的理由：

- 线索句取自按需加载的单元详情包（`src/data/chars/uN.js`）里的字义，掐到 16 字以内；
  运行时只看得到主包里的字表索引，说不出「铃」是「叮叮当当响的小铃铛」。
- 玩法只在字源说得上话时纠三处，其余沿用引擎的主题轮转（轮转本来就铺得开）：
  1. 有小图的象形 / 指事字 → `morph-story`（本来就是照着东西画的）
  2. 形声 / 会意字轮到 `morph-story` → 改 `drag-parts`（把管意思的形旁拼回去）
  3. 轮到 `drag-parts` 却没有部件可讲 → 改 `emoji-hunt` / `tap-reveal`

## 富脚本道具适配（顺手修的集成缝）

富脚本写道具用的是情境小词汇（`hero` / `items` / `stages` / `target` / `decoys` / `goal`），
舞台吃的是模板道具（`items` / `frames` / `cells` / `options` / `drops`）。合入时两边直接
`{...base.props, ...rich.props}`，于是 47 个字拿到点不动的卡片（`npm run test:play` 在
编排分支 @ 89d2546 上红 47 处）。本分支按模板翻译，翻不出来退回模板道具，旁白与主角图标
仍是手写的那份；富脚本自己的 11 种玩法名（`count-tap` / `swipe-motion` / `pop-bubbles`…）
映射到舞台最接近的机制。

## 实测（`/tmp/wt-r15-autofill`，node v22）

```
$ npm run gen:char-play
Play 补齐索引已生成：1820 字全覆盖（字义线索 1818，按字源改写玩法 402）。
  模板 5 种：tap-reveal 534，emoji-hunt 470，drag-parts 352，morph-story 306，rain-catch 158
  主题 17 类：nature 320，action 233，body 195，home 164，family 162，number 133，tool 115，water 103

$ npm run verify:char-play
✓ char-play-generated.js 是最新的（1820 字）

$ npm run test:play
char-play 自测：1820 字，模板分布 tap-reveal 609 / emoji-hunt 433 / drag-parts 322 / morph-story 298 / rain-catch 158
富脚本 272 条，模板补齐 1548 字，空洞 0
✓ 全库每个字都有玩得完的场景          ← 编排分支同一命令为 ✗ 47 处不合格

$ npm run check:data
  ✓ Play 补齐索引覆盖全库 1820/1820
  ✓ Play 旁白一字一句：1820/1820 条不重样（要求 ≥ 95%）
  ✓ 字表外的字也有兜底 Play，且标了 templateFallback
  ✓ Play 补齐索引与生成器一致
内容自检：84 项通过，0 项失败。

$ npm run build && npm run check:bundle
  ✓ 首屏 JS 325 KB（预算 420 KB）              ← 与编排分支持平，补齐索引不进首屏
构建产物体检：4 项通过，0 项失败。

$ npm run check:round15   （仓库根）
Round 15 check (ROUND15-v1.1): 7/8      ← 仅 H8 红：worktree 里没有 android:sim 产的双 APK，
                                           同一提交在 /workspace（有 APK）check:round13 为 7/8
```

## 包体账

| 块 | 编排分支 @ 89d2546 | 本分支 | 差 |
|---|---|---|---|
| 首屏 `index-*.js` | 325 KB | 325 KB | 0 |
| `CharDetailView-*.js`（按需） | 136.1 KB / gzip 44.7 | 177.6 KB / gzip 70.6 | +41.5 KB / +25.9 KB |

多出来的就是 1820 句线索。首屏预算不受影响；这一块随「玩」步按需下载，离线预缓存照旧。

**给后续接手的人**：`char-play.js` 只能从 `CharPlayStage` / `CharDetailView` 这类懒加载路由
引用，别从首页地图或 `CharCard` 引用——那样补齐索引会被拉进首屏块，425 KB 就顶到预算线了。

## 重跑

```
cd apps/literacy-app
npm run gen:char-play      # 字表 / 课文 / 字源 改了都要重跑
npm run verify:char-play   # 只校验是不是最新（check:data 里也会跑一遍）
```
