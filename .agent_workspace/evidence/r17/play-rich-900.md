# Round 17 · H2 富 Play 从 640 扩到 940 条（u1–u55）

分支：`cursor/r17-play-rich-900-9f67`（基线 `cursor/r17-orchestration-9f67` @ f9f8cf1）
Model slug：claude-opus-5-thinking-high-fast（子代理 #4）
门槛：`countRichPlays() ≥ 900`，narration 去重 ≥ 720，可执行 `ROUND17_H2` 标记

## 结论

| 口径 | R16 | 本批 |
|---|---|---|
| 手写富脚本 | 640 条（u1–u40） | **940 条（u1–u55）** |
| 旁白不重样 | 640 | **940**（撞句率 0） |
| 模板补齐（`templateFallback: true`） | 1180 字 | 880 字 |
| 全库空洞 | 0 | 0 |
| 撞句拦截 | 一字不差判错 | **一字不差 + 只差标点语气都判错**，且落盘前再核一次 |

`check-round17.mjs` 的 H2 从红转绿：`✓ H2 富 Play 940 ≥ 900，narration 去重 940 ≥ 720`。

## 实测

```
$ npm --prefix apps/literacy-app run check:play:rich
[play-rich] seed 校验通过：940 条，覆盖 55 个单元、16 个模板，旁白 940 句不重样。

$ npm --prefix apps/literacy-app run gen:play:rich
[play-rich] 940 条富脚本，覆盖 55 个单元（u1–u55），约 256 KB。
[play-rich] 模板分布：count-tap 95、swipe-motion 158、morph-story 31、sound-tap 40、
grow-tap 81、emoji-hunt 56、tap-reveal 73、drag-parts 67、trace-path 64、scene-poke 67、
sort-buckets 60、pair-match 46、pop-bubbles 48、rain-catch 17、word-build 8、color-fill 29

$ npm --prefix apps/literacy-app run test:play
char-play 自测：1820 字
  模板 19 种 / 互动 6 种：pick 602 / catch 433 / assemble 310 / push 222 / watch 147 / match 106
  来源：rich 940 / generated 880（模板补齐 880 字，空洞 0）
✓ 全库每个字都有玩得完的场景

$ npm --prefix apps/literacy-app run test:play:guard
真 seed：940 条 / 55 个单元 / 旁白 940 句不重样
运行时：ROUND17_H2 · 940 条 / 旁白 940 句不重样
✓ 撞句与条数不足都在生成期被拦下，真 seed 达线

$ node -e "…char-play.js…"
{"probe":"ROUND17_H2","plays":940,"narrations":940}
countRichPlays = 940；templateFallback ≠ false 的 0 条；char 去重 940；覆盖 55 个单元

$ node scripts/check-round17.mjs
✓ H2 富 Play 940 ≥ 900，narration 去重 940 ≥ 720

$ node scripts/check-round16.mjs
✓ H3 富 Play 940 ≥ 500，narration 去重 940 ≥ 400

$ node scripts/check-round15.mjs
✓ H3 富 play 脚本 940 ≥ 200，narration 去重 940 ≥ 160（runtime，fallback=880）

$ npm --prefix apps/literacy-app run check:data
内容自检：80 项通过，0 项失败。

$ npm --prefix apps/literacy-app run build && npm --prefix apps/literacy-app run check:bundle
✓ 首屏 JS 325 KB（预算 420 KB）；构建产物体检：4 项通过，0 项失败。
```

## 撞句是在生成期拦的，不是事后数出来的

探针数「940 条 / 940 句不重样」，这两个数各自都骗得过：同一句复制 300 遍，
条数够；把句号换成感叹号，「一字不差」的去重也放行——可念给孩子听还是同一句。
所以本轮把闸门加在 `gen-char-play-rich.mjs` 的解析环节，seed 有问题就不生成：

1. `narrationOwner` —— 一字不差的撞句，报「和「X」一字不差，换一句」；
2. `narrationKey()` —— 去掉标点、空格和句尾语气词再比，近似撞句报
   「和「X」只差标点语气，念出来是同一句」；
3. 落盘前再核一次「归一后去重数 == 条数」，以及 900 / 720 两条线不到就退出 1。

`scripts/test-play-rich-guard.mjs` 是这三道闸的负例自测：把 seed 改坏（复制旁白、
只改标点、砍到 899 条）跑生成器，三种都必须非零退出，真 seed 则必须报满 940 /
940 且和运行时 `richPlayCoverage()` 对得上。已挂进 `literacy-app` 的 `test` 链
（`test:play` 之后），以后撞句混不进来。

## 新写的 300 条长什么样

标准和 R15/R16 一样：**玩法本身就在解释这个字**，不是「换张卡片配句旁白」。

```
疾|feeling|grow-tap|疾是又急又重的病，别拖着。|stages=😀,🤧,🤒;goal=3
析|action|drag-parts|把「析」拆开，看清楚零件。|hero=🔬;parts=木,斤
端|action|trace-path|端着水杯慢慢走，别洒了。|hero=🥛;dir=right;goal=3
划|action|swipe-motion|两只桨往后划，船就前进。|hero=🛶;dir=left;goal=4
余|number|pop-bubbles|分完还剩两个，这就叫余。|hero=🍡;items=🍡,🍡;goal=2
峡|nature|drag-parts|两边山夹一条水，就是峡。|hero=🏞️;parts=⛰️,🌊,⛰️
彩|color|morph-story|白光穿过水珠，变出七彩。|stages=⬜,💧,🌈;goal=3
```

- 「析」是左木右斤，拼零件玩的就是这两个部件，拖对了字义自己就出来了；
- 「划」的方向故意设成 `left`：桨往后划、船才往前，划反了就不是这个字的意思；
- 「余」只摆两颗丸子，孩子点完剩下的那两个就是「余」，不用讲除法也懂；
- 「峡」的三个零件是山—水—山，摆好就是「两山夹一水」。

新增 300 条的分布：

| 口径 | 数 |
|---|---|
| 模板 | swipe-motion 59、count-tap 36、grow-tap 30、trace-path 21、emoji-hunt 20、sort-buckets 18、pair-match 17、drag-parts 17、scene-poke 17、pop-bubbles 15、morph-story 14、tap-reveal 12、color-fill 11、sound-tap 10、word-build 2、rain-catch 1 |
| 交互 | tap 151 / drag 76 / swipe 59 / sequence 14 |
| 旁白长度 | 9–15 字，平均 12.1 字（上限 26） |

覆盖单元：u41 看病和健康、u42 逛商店、u43 写信和消息、u44 过节和礼貌、
u45 我们的国家、u46 荒野和大地、u47 鸟兽虫鱼、u48 花木和果子、u49 房子里外、
u50 灶台和收拾、u51 音乐和画画、u52 运动会、u53 用心想一想、u54 从前和现在、
u55 量一量比一比。

## 代价：单字页那个懒加载块大了 13 KB（gzip）

同一台机器上分别构建基线和本批：

| 产物 | 基线 f9f8cf1 | 本批 | 差 |
|---|---|---|---|
| 首屏 `index-*.js` | 314.49 kB（gzip 111.13） | 314.49 kB（gzip 111.12） | 不动 |
| `CharDetailView-*.js`（懒加载） | 279.05 kB（gzip 99.02） | 332.89 kB（gzip 111.82） | +53.8 kB（gzip **+12.8 kB**） |

首屏没受影响（`check:bundle` 的 420 KB 预算仍有 95 KB 余量）；涨的是点进单字页
才拉的那个块。300 条手写剧本换 12.8 KB gzip，这个价现在划算，但**再往后扩就该
按单元切块了**——u56 以后继续一条一条加，这个块会线性长下去，低端机首次进单字页
的等待会先被拖慢。建议下一轮（或 R17 的架构岗）把 `char-play-rich.js` 按单元
分片、跟着课文块一起懒加载，扩到 1820 全覆盖才不会撞墙。

## 没跑的 / 不归本批的

- `npm run smoke`（无头 Chrome 走全路由）：几路兄弟子代理同机在跑，再起一份只会
  互相抢内存。本批是纯数据 + 生成器改动，舞台组件一行没动，运行时侧由 `test:play`
  全库 1820 字兜住（0 空洞，六种 kind 的道具逐条校验），合入编排分支时随大盘跑。
- `check:round16` 在这台机器上是 **7/8**：红的是 H8（连锁到 round13 H6，干净环境
  需先 `npm run android:sim` 重建双 APK）。**基线上同样红**，不是本批引入；归
  regression-gate 岗（子代理 #10）。本批关心的 R16 H3 是绿的（940 ≥ 500）。
- `test-round16-smoke.mjs` 的第 6 项（H7 家长周报）在**基线上就红**，本批未触碰。
  基线与本批都是 5/6 通过。
