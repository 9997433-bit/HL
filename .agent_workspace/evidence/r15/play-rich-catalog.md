# Round 15 · H3 富互动 play 脚本批次（u1–u20）

分支：`cursor/r15-play-catalog-rich-9f67`（基线 `cursor/r15-orchestration-9f67` @ 8e30519）
Model slug：claude-opus-5-thinking-high-fast

## 交付

| 文件 | 作用 |
|---|---|
| `apps/literacy-app/scripts/data/char-play-seed.txt` | 手写剧本 seed，272 条（前 20 个单元全覆盖），一字一条 |
| `apps/literacy-app/scripts/gen-char-play-rich.mjs` | 解析 + 校验 + 落盘（`npm run gen:play:rich` / `--check`） |
| `apps/literacy-app/src/data/char-play-rich.js` | 生成物：`CHAR_PLAY_RICH` / `RICH_PLAY_BY_CHAR` / `getRichPlay` / `countRichPlays` / `PLAY_TEMPLATES` |

实测：

```
$ npm run gen:play:rich
[play-rich] 272 条富脚本，覆盖 20 个单元（u1–u20），约 76 KB。
[play-rich] 模板分布：count-tap 23、swipe-motion 38、morph-story 7、sound-tap 19、grow-tap 17、
emoji-hunt 17、tap-reveal 34、drag-parts 23、trace-path 10、scene-poke 24、sort-buckets 16、
pair-match 14、pop-bubbles 13、rain-catch 6、word-build 4、color-fill 7

$ node scripts/check-round15.mjs
✓ H3 富 play 脚本 272 ≥ 200

$ node apps/literacy-app/scripts/check-data.mjs
内容自检：80 项通过，0 项失败。
```

## 脚本和字义怎么挂钩

每条剧本是照着这个字的意思设计的，不是套壳：

| 字 | 模板 | 玩什么 |
|---|---|---|
| 雨 | `rain-catch` | 撑伞接住 4 滴雨 |
| 火 | `grow-tap` | 添柴，火苗 🕯️→🔥→🌋 越烧越大 |
| 口 | `sound-tap` | 点嘴巴张开发「啊」 |
| 人 | `morph-story` | 🧍→🚶→人，小人走成字形 |
| 林 | `drag-parts` | 拖两个「木」并排 |
| 推 / 拉 | `swipe-motion` | 一个向右推、一个向左拉 |
| 多 / 少 | `sort-buckets` / `pop-bubbles` | 一个分多少堆、一个越点越少 |
| 双 | `pair-match` | 袜子鞋子手套两两配成一双 |

## 给 #4（引擎）和 #7（自动补齐）的接口约定

```js
import { getRichPlay, countRichPlays, PLAY_TEMPLATES } from '@/data/char-play-rich.js'
```

- 条目形状：`{ char, unit, theme, template, interaction, narration, props, templateFallback: false }`
- `interaction` ∈ `tap | drag | swipe | sequence`。**某个 template 的专属动效还没实现时，
  按 interaction 退回通用演法**，孩子照样玩得完——不能退成空白卡（Round 15 红线）。
- `props.goal` 一定是数字：要完成几次有效交互才算通关。seed 没写的由生成器按模板推
  （拼 3 块就是 3 下，接 4 滴就是 4 下），所以舞台不必自己猜。
- `props.hero` 一定有：seed 没写的回填成字表里的卡片 emoji，保证有主角可画。
- emoji 走 `@shared/components/OpenMojiIcon.vue`；映射表里没有的会自动退回系统 emoji 文本，
  不需要为这 272 条补 SVG。
- `char-play.js`（#7）建议：先查 `getRichPlay(char)`，命中就直接用；没命中再按部首 / 主题
  生成 `templateFallback: true` 的兜底条目。H3 数的是 `templateFallback: false` 那一层。

## 包体

生成物 76 KB 源码（压缩后约 12 KB gzip）。它只该被「玩」这一步的舞台引用，
`check-bundle.mjs` 的首屏预算按 CharDetailView 走懒加载路由算——如果 #4 把它接进了
同步入口，记得改成 `import()`。

## 后续可扩

`RICH_UNIT_LIMIT = 20` 是手写覆盖的边界，往后写 u21+ 时改这个常量，校验会跟着放宽。
seed 的行格式和 `char-seed.txt` 一脉（`|` 分段 + `#` 注释），可以直接续写。
